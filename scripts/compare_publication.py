"""Compare complete Pages publications using uncompressed bytes and SHA-256."""
import argparse
import csv
import gzip
import hashlib
import io
import json
import re
from pathlib import Path
from migrate_darktide_skills import load_routes, apply_migration


def normalize_build_time(path, raw):
    """Normalize only existing volatile fields for regression comparison, never accounting."""
    if path.endswith(".html"):
        return re.sub(br'(/assets/(?:css/style\.css|js/article-word-breaks\.js)\?v=)\d+(?=["\'])', br'\g<1>BUILD_TIME', raw)
    if path == "feed.xml":
        return re.sub(br'<updated>[^<]+</updated>', b'<updated>BUILD_TIME</updated>', raw)
    if path == "sitemap.xml":
        return re.sub(br'<lastmod>[^<]+</lastmod>', b'<lastmod>BUILD_TIME</lastmod>', raw)
    return raw


def inventory(root):
    return {p.relative_to(root).as_posix(): {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in sorted(root.rglob("*")) if p.is_file()}


def write_table(path, rows, fields):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    raw = buffer.getvalue().encode("utf-8")
    path.write_bytes(gzip.compress(raw, mtime=0) if path.suffix == ".gz" else raw)


def compare(before_root, after_root, output):
    before, after = inventory(before_root), inventory(after_root)
    output.mkdir(parents=True, exist_ok=True)
    for name, values in (("before", before), ("after", after)):
        write_table(output / (name + "-publication.csv.gz"),
                    ({"path": path, **meta} for path, meta in values.items()), ["path", "bytes", "sha256"])
    redirects = {row["old"].strip("/") + "/index.html" for row in load_routes(Path(__file__).resolve().parents[1])}
    allowed = redirects | {"darktide/index.html", "darktide/en/index.html", "darktide/sitemap-001.xml", "assets/js/darktide-navigation.js"}
    changes = []
    unexpected = []
    build_time_only = []
    for path in sorted(before.keys() | after.keys()):
        old, new = before.get(path, {}), after.get(path, {})
        if old == new:
            continue
        retained_skill = path.startswith("darktide/skills/") and path.endswith("/index.html") and path not in redirects
        time_only = (old and new and normalize_build_time(path, (before_root / path).read_bytes()) == normalize_build_time(path, (after_root / path).read_bytes()))
        if time_only:
            build_time_only.append(path)
        if path not in allowed and not retained_skill and not time_only:
            unexpected.append(path)
        changes.append({"path": path, "kind": "build-time-only" if time_only else "redirect" if path in redirects else "retained-directory-or-supplement" if retained_skill else "navigation-or-sitemap" if path.startswith(("darktide/", "assets/")) else "jekyll-generated", "before_bytes": old.get("bytes",0), "after_bytes": new.get("bytes",0), "delta_bytes": new.get("bytes",0)-old.get("bytes",0), "before_sha256": old.get("sha256",""), "after_sha256": new.get("sha256","")})
    write_table(output / "changed-files.csv", changes, ["path","kind","before_bytes","after_bytes","delta_bytes","before_sha256","after_sha256"])
    shared = [{"path":path, **meta, "status":"unchanged" if before.get(path)==meta else "updated-navigation"} for path,meta in after.items() if path.startswith("assets/")]
    write_table(output / "retained-shared-assets.csv.gz", shared, ["path","bytes","sha256","status"])
    apply_migration(after_root, check=True)
    if set(before) != set(after):
        raise ValueError("Unexpected file creation/deletion; inspect full manifests")
    if unexpected:
        raise ValueError("Unrelated publication changed: " + ", ".join(unexpected[:10]))
    summary = {"basis":"Same Pages build action, raw uncompressed publication bytes; all regular files included", "before":{"files":len(before),"bytes":sum(x["bytes"] for x in before.values())},"after":{"files":len(after),"bytes":sum(x["bytes"] for x in after.values())}, "redirects":{"files":len(redirects),"before_bytes":sum(before[p]["bytes"] for p in redirects),"after_bytes":sum(after[p]["bytes"] for p in redirects)},"changed_files":len(changes),"retained_shared_assets":{"files":len(shared),"bytes":sum(x["bytes"] for x in shared)},"unexpected_changes":unexpected,"excluded_accounts":["new standalone site","retained Cloudflare versions","GitHub backups","Git history","ZIP bytes","HTTP compression"],"build_time_only_changes":build_time_only}
    summary["reduction_bytes"] = summary["before"]["bytes"] - summary["after"]["bytes"]
    (output / "summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))

if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before",type=Path)
    parser.add_argument("after",type=Path)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    compare(args.before,args.after,args.output)
