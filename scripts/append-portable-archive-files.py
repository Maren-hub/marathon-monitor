from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


project_root = Path(r"D:\创新设计大赛\marathon monitor")
archive = Path(r"D:\创新设计大赛\智跑慧巡平台_同伴电脑完整包_最终版.zip")

files = [
    (project_root / "START_PLATFORM.bat", "marathon monitor/START_PLATFORM.bat"),
    (project_root / "TEAMMATE_README.txt", "marathon monitor/TEAMMATE_README.txt"),
]

with ZipFile(archive, mode="a", compression=ZIP_DEFLATED, allowZip64=True) as zip_file:
    existing = {entry.filename for entry in zip_file.infolist()}
    for source, destination in files:
        if destination not in existing:
            zip_file.write(source, destination)

print(archive)
