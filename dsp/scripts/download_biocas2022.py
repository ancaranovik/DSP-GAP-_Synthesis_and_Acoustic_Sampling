"""Tải BioCAS2022 ở commit cố định và lưu checksum; không phân tích audio.

Chạy: python dsp/scripts/download_biocas2022.py
--source-repo dùng bản SPRSound Git đã tải để tránh tải lại.
Raw đang có chỉ được giữ nếu byte khớp nguồn; không ghi đè file khác.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

REPOSITORY = "https://github.com/SJTU-YONGFU-RESEARCH-GRP/SPRSound"
COMMIT = "bca1e51422a42a042441010081519610ef3845d0"


def git(repo, *args):
    """Chạy Git trong thư mục nguồn chỉ định."""
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def prepare_source(root, supplied_repo):
    """Dùng repo có sẵn hoặc tải riêng BioCAS2022 vào cache của dự án."""
    if supplied_repo is not None:
        source = supplied_repo.expanduser().resolve()
        git(source, "cat-file", "-e", COMMIT + "^{commit}")
        return source
    source = root / ".cache" / "sprsound"
    fresh = not source.exists()
    if fresh:
        source.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout",
                        REPOSITORY + ".git", str(source)], check=True)
    if git(source, "remote", "get-url", "origin").removesuffix(".git") != REPOSITORY:
        raise ValueError("Cache có remote khác; không tự thay hoặc ghi đè cache.")
    if not fresh and git(source, "status", "--porcelain"):
        raise ValueError("Cache có thay đổi; dùng --source-repo hoặc kiểm tra trước.")
    try:
        git(source, "cat-file", "-e", COMMIT + "^{commit}")
    except subprocess.CalledProcessError:
        git(source, "fetch", "origin", COMMIT)
    git(source, "sparse-checkout", "set", "--no-cone", "/BioCAS2022/", "/README.md", "/LICENSE")
    git(source, "-c", "core.autocrlf=false", "checkout", "--detach", COMMIT)
    return source


def export_dataset(root, source):
    """Xuất byte Git gốc, kiểm hash từng file và tạo manifest cho notebook 01."""
    destination = root / "dsp/data/raw"
    report = root / "dsp/outputs/reports/download_biocas2022.json"
    if report.exists():
        raise FileExistsError(f"Đã có manifest; không ghi đè: {report}")
    listing = git(source, "ls-tree", "-r", COMMIT, "--", "BioCAS2022", "README.md", "LICENSE")
    counts, inventory = Counter(), []
    with subprocess.Popen(["git", "-C", str(source), "cat-file", "--batch"],
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE) as reader:
        try:
            for line in listing.splitlines():
                metadata, relative = line.split("\t", 1)
                mode, kind, expected = metadata.split()
                if kind != "blob" or mode not in {"100644", "100755"}:
                    raise ValueError(f"Git entry không hỗ trợ: {relative}")
                reader.stdin.write((expected + "\n").encode("ascii"))
                reader.stdin.flush()
                header = reader.stdout.readline().decode("ascii").strip().split()
                if len(header) != 3 or header[0] != expected or header[1] != "blob":
                    raise ValueError(f"Không đọc được Git blob: {relative}")
                size = int(header[2])
                content = reader.stdout.read(size)
                if len(content) != size or reader.stdout.read(1) != b"\n":
                    raise ValueError(f"Git blob chưa đủ byte: {relative}")
                actual = hashlib.sha1(f"blob {size}\0".encode("ascii") + content).hexdigest()
                if actual != expected:
                    raise ValueError(f"Git hash không khớp: {relative}")
                if relative.endswith(".wav") and not (content[:4] in {b"RIFF", b"RF64"} and content[8:12] == b"WAVE"):
                    raise ValueError(f"Không phải WAV, có thể là LFS pointer: {relative}")
                local = {"README.md": "SPRSound_README.md", "LICENSE": "SPRSound_LICENSE"}.get(relative, relative)
                target = (destination / local).resolve()
                if not target.is_relative_to(destination.resolve()):
                    raise ValueError(f"Đường dẫn ra ngoài raw: {relative}")
                target.parent.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256(content).hexdigest()
                if target.exists():
                    if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                        raise ValueError(f"File hiện có khác nguồn; không ghi đè: {target}")
                else:
                    with target.open("xb") as file:
                        file.write(content)
                if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                    raise ValueError(f"Checksum sau ghi không khớp: {relative}")
                group = "/".join(relative.split("/")[:2]) if relative.count("/") >= 2 else relative
                counts[group] += 1
                inventory.append(dict(repo_path=relative, local_path=target.relative_to(root).as_posix(),
                                      bytes=size, git_blob_sha1=expected, sha256=digest))
                if len(inventory) % 500 == 0:
                    print(f"Verified {len(inventory)} files", flush=True)
        finally:
            reader.stdin.close()
            reader.stdout.close()
        if reader.wait() != 0:
            raise RuntimeError("git cat-file thất bại")
    wanted = {"BioCAS2022/train2022_wav": 1949, "BioCAS2022/train2022_json": 1949,
              "BioCAS2022/test2022_wav": 734, "BioCAS2022/test2022_json": 734}
    if any(counts[k] != v for k, v in wanted.items()) or len(inventory) != 5369:
        raise ValueError(f"Số file khác release đã kiểm: {dict(counts)}")
    summary = dict(repository=REPOSITORY, commit=COMMIT,
                   verified_at_utc=datetime.now(timezone.utc).isoformat(),
                   method="Pinned Git source; original blob bytes exported with git cat-file --batch",
                   status="download_byte_integrity_verified",
                   scope="Byte integrity and WAV container signatures only; no test audio decoding or analysis.",
                   total_files=len(inventory), total_bytes=sum(r["bytes"] for r in inventory),
                   counts=dict(counts), files=inventory)
    report.parent.mkdir(parents=True, exist_ok=True)
    with report.open("x", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)
        file.write("\n")
    print(f"Ready: {len(inventory)} files, {summary['total_bytes']:,} bytes; manifest: {report}")


def main():
    """Nhận đường dẫn nguồn tùy chọn, không xử lý nặng khi import module."""
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-repo", type=Path, help="Bản Git SPRSound đã có commit nguồn")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if (root / "dsp/outputs/reports/download_biocas2022.json").exists():
        raise SystemExit("Manifest đã tồn tại. Dùng dataset hiện có; không tải hoặc ghi đè.")
    export_dataset(root, prepare_source(root, args.source_repo))


if __name__ == "__main__":
    main()
