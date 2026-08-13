"""클라이언트 배포 zip 빌드 — Windows/맥 분리.

맥 zip은 .command 파일에 유닉스 실행 권한(0755)을 심어서
macOS 기본 압축 해제 후 바로 더블클릭 실행이 되게 한다.
(PowerShell Compress-Archive는 유닉스 권한을 못 넣음)

사용: python tools/build_client_zips.py [readme_win.txt readme_mac.txt]
      README 인자 생략 시 client/README.txt를 양쪽에 사용.
"""
import sys
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CLIENT = BASE / "client"

WIN_FILES = ["receiver.py", "setup.bat", "run.bat"]
MAC_FILES = ["receiver.py", "setup_mac.command", "run_mac.command"]
MAC_EXEC = {"setup_mac.command", "run_mac.command"}


def add_entry(zf: zipfile.ZipFile, src: Path, arcname: str, executable: bool):
    data = src.read_bytes()
    info = zipfile.ZipInfo(arcname)
    info.compress_type = zipfile.ZIP_DEFLATED
    if executable:
        info.create_system = 3          # unix — 권한 비트를 존중하게 함
        info.external_attr = 0o755 << 16
    else:
        info.external_attr = 0o644 << 16
        info.create_system = 3
    zf.writestr(info, data)


def build(zip_path: Path, files: list[str], readme: Path | None, exec_set: set[str]):
    zip_path.unlink(missing_ok=True)
    with zipfile.ZipFile(zip_path, "w") as zf:
        for name in files:
            add_entry(zf, CLIENT / name, name, name in exec_set)
        if readme and readme.exists():
            add_entry(zf, readme, "README.txt", False)
    print(f"{zip_path.name}: {[i.filename for i in zipfile.ZipFile(zip_path).infolist()]}")


if __name__ == "__main__":
    readme_win = Path(sys.argv[1]) if len(sys.argv) > 1 else CLIENT / "README.txt"
    readme_mac = Path(sys.argv[2]) if len(sys.argv) > 2 else CLIENT / "README.txt"
    build(BASE / "picpod_client_win.zip", WIN_FILES, readme_win, set())
    build(BASE / "picpod_client_mac.zip", MAC_FILES, readme_mac, MAC_EXEC)
