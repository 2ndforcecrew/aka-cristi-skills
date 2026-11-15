"""Safe, stdlib-only local Skill installer (preview-by-default).

Supports Codex user skills and explicitly supplied local skills roots.
Never installs from network, runs source scripts or changes host configuration.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
import uuid
from pathlib import Path

NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
STATE = ".aka-skill-installer"
LIMIT_BYTES = 12 * 1024 * 1024


class InstallError(ValueError):
    pass


def checked(path):
    p = Path(os.path.abspath(os.path.expanduser(str(path))))
    ancestor = p
    while True:
        if ancestor.is_symlink():
            raise InstallError("symlink destination/source forbidden")
        if ancestor.parent == ancestor:
            break
        ancestor = ancestor.parent
    return p


def package(source, expected_name=None):
    src = checked(source)
    if not src.is_dir() or not (src / "SKILL.md").is_file():
        raise InstallError("expected local directory with SKILL.md")
    data = (src / "SKILL.md").read_text(encoding="utf-8")
    if not data.startswith("---\n") or "\n---\n" not in data[4:]:
        raise InstallError("invalid SKILL.md frontmatter")
    header = data[4:].split("\n---\n", 1)[0]
    meta = {}
    for line in header.splitlines():
        if not line.strip():
            continue
        if ":" not in line or line[0].isspace():
            raise InstallError("unsupported frontmatter")
        key, val = line.split(":", 1)
        if key in meta:
            raise InstallError("duplicate metadata")
        meta[key] = val.strip().strip("'\"")
    name = meta.get("name", "")
    if not NAME.fullmatch(name) or len(name) > 64 or name != (expected_name or src.name):
        raise InstallError("skill name must match directory")
    if not meta.get("description"):
        raise InstallError("skill description required")
    digest = hashlib.sha256()
    size = 0
    count = 0
    for folder, dirs, files in os.walk(src, followlinks=False):
        for dirname in dirs:
            p = Path(folder) / dirname
            if p.is_symlink() or dirname in (".git", "__pycache__", STATE):
                raise InstallError("unsafe directory in package")
        for filename in files:
            p = Path(folder) / filename
            if p.is_symlink() or not p.is_file() or any(ord(c)<32 for c in filename):
                raise InstallError("unsafe file in package")
            count += 1
            if count > 100 or p.stat().st_size > 2*1024*1024:
                raise InstallError("too many or oversized files")
            size += p.stat().st_size
            if size > LIMIT_BYTES:
                raise InstallError("oversized package")
            rel = p.relative_to(src).as_posix()
            digest.update(rel.encode() + b"\0" + hashlib.sha256(p.read_bytes()).digest())
    return {"source": src, "name": name, "sha256": digest.hexdigest(), "files": count}


def root_for(target, root=None):
    if target == "codex":
        if root is not None:
            raise InstallError("codex target uses user skills directory; use directory for explicit path")
        return checked(Path.home() / ".agents" / "skills")
    if target == "directory" and root is not None:
        return checked(root)
    raise InstallError("directory target needs --root")


def load_state(root):
    p = checked(root / STATE / "state.json")
    if not p.exists():
        return {"version": 1, "installed": {}}
    obj = json.loads(p.read_text(encoding="utf-8"))
    if (not isinstance(obj, dict) or obj.get("version") != 1
            or not isinstance(obj.get("installed"), dict)):
        raise InstallError("unrecognized state")
    return obj


def persist(root, state):
    folder = checked(root / STATE)
    folder.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="state-", dir=folder)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump(state,f,indent=2,sort_keys=True)
            f.write("\n")
        os.replace(tmp,folder/"state.json")
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def inspect(source, target="directory", root=None):
    info = package(source)
    destination = root_for(target,root)
    state = load_state(destination)
    name = info["name"]
    managed = state["installed"].get(name)
    installed = destination / name
    if installed.is_symlink():
        raise InstallError("symlink installed skill")
    if installed.exists():
        if not managed:
            action = "conflict_unmanaged"
        elif package(installed)["sha256"] != managed["sha256"]:
            action = "conflict_modified"
        elif managed["sha256"] == info["sha256"]:
            action = "already_installed"
        else:
            action = "upgrade"
    elif managed:
        action = "conflict_missing"
    else:
        action = "install"
    return {"action":action,"name":name,"root":str(destination),
            "sha256":info["sha256"],"files":info["files"]}


def install(source,target="directory",root=None,apply=False):
    plan=inspect(source,target,root)
    if not apply or plan["action"]=="already_installed":
        return {**plan,"applied":False}
    if plan["action"].startswith("conflict"):
        raise InstallError("existing files unmanaged or modified; refusing overwrite")
    info=package(source)
    destination=root_for(target,root)
    destination.mkdir(parents=True,exist_ok=True)
    folder=checked(destination/STATE)
    folder.mkdir(exist_ok=True)
    backup_dir=checked(folder/"backups")
    backup_dir.mkdir(exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix="stage-",dir=folder))
    saved=None
    target_path=destination/info["name"]
    state=load_state(destination)
    try:
        shutil.copytree(info["source"],stage/info["name"])
        if package(stage/info["name"])["sha256"] != info["sha256"]:
            raise InstallError("source changed during copy")
        if target_path.exists():
            saved=backup_dir/(info["name"]+"-"+uuid.uuid4().hex)
            os.replace(target_path,saved)
        try:
            os.replace(stage/info["name"],target_path)
            state["installed"][info["name"]]={"sha256":info["sha256"],
                "backup": saved.name if saved else None}
            persist(destination,state)
        except Exception:
            if target_path.exists():
                shutil.rmtree(target_path)
            if saved and saved.exists():
                os.replace(saved,target_path)
            raise
    finally:
        shutil.rmtree(stage,ignore_errors=True)
    return {**plan,"applied":True,"backup":saved.name if saved else None,
            "activation":"NOT_RUN"}


def managed(name,target,root):
    if not NAME.fullmatch(name):
        raise InstallError("invalid skill name")
    dest=root_for(target,root)
    rec=load_state(dest)["installed"].get(name)
    if rec is None:
        raise InstallError("skill not installed by this tool")
    if package(dest/name)["sha256"] != rec["sha256"]:
        raise InstallError("installed skill externally modified")
    return dest,rec


def verify(name,target="directory",root=None):
    _,rec=managed(name,target,root)
    return {"name":name,"integrity":"PASS","activation":"NOT_RUN",
            "sha256":rec["sha256"]}


def remove(name,target="directory",root=None,apply=False):
    dest,rec=managed(name,target,root)
    result={"name":name,"action":"uninstall","applied":False}
    if not apply:
        return result
    archive=checked(dest/STATE/"backups"/(name+"-"+uuid.uuid4().hex))
    os.replace(dest/name,archive)
    state=load_state(dest)
    del state["installed"][name]
    try:
        persist(dest,state)
    except Exception:
        os.replace(archive,dest/name)
        raise
    return {**result,"applied":True,"archive":str(archive)}


def rollback(name,target="directory",root=None,apply=False):
    dest,rec=managed(name,target,root)
    backup=rec.get("backup")
    if not isinstance(backup,str) or not re.fullmatch(re.escape(name)+r"-[a-f0-9]{32}",backup):
        raise InstallError("no prior backup")
    previous=checked(dest/STATE/"backups"/backup)
    if not previous.is_dir():
        raise InstallError("previous version backup missing")
    old=package(previous, expected_name=name)
    result={"name":name,"action":"rollback","applied":False,"sha256":old["sha256"]}
    if not apply:
        return result
    swap=checked(dest/STATE/"backups"/(name+"-"+uuid.uuid4().hex))
    os.replace(dest/name,swap)
    try:
        os.replace(previous,dest/name)
        state=load_state(dest)
        state["installed"][name]={"sha256":old["sha256"],"backup":swap.name}
        persist(dest,state)
    except Exception:
        if (dest/name).exists():
            os.replace(dest/name,previous)
        os.replace(swap,dest/name)
        raise
    return {**result,"applied":True}


def main(argv=None):
    parser=argparse.ArgumentParser(description="AKA.CRISTI safe local Skill installer")
    parser.add_argument("action",choices=["preview","install","verify","uninstall","rollback"])
    parser.add_argument("value",help="source path for preview/install, skill name otherwise")
    parser.add_argument("--target",choices=["codex","directory"],default="directory")
    parser.add_argument("--root",type=Path)
    parser.add_argument("--apply",action="store_true",help="explicitly authorize filesystem edits")
    args=parser.parse_args(argv)
    try:
        if args.action=="preview":
            result=inspect(args.value,args.target,args.root)
        elif args.action=="install":
            result=install(args.value,args.target,args.root,args.apply)
        elif args.action=="verify":
            result=verify(args.value,args.target,args.root)
        elif args.action=="uninstall":
            result=remove(args.value,args.target,args.root,args.apply)
        else:
            result=rollback(args.value,args.target,args.root,args.apply)
        print(json.dumps(result,indent=2))
        return 0
    except (InstallError,OSError,ValueError,UnicodeError) as exc:
        print(json.dumps({"error_type":type(exc).__name__,"status":"FAIL"}))
        return 1


if __name__=="__main__":
    raise SystemExit(main())
