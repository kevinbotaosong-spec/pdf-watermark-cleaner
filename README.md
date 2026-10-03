# PDF 水印清理 (macOS)

一个极简的本地 PDF 水印移除工具。拖入 PDF 后自动处理，并在原文件夹生成 `*_clean.pdf`；不会覆盖原文件，也不会上传 PDF。

## 它适合什么水印？

当前版本采用**安全模式**：移除 PDF content stream 中明确标记为 `/Artifact` + `/Subtype /Watermark` 的标准水印对象，以及标准 Watermark annotation。

这正是很多扫描/导出软件（包括本项目测试样本）使用的结构。它不会因为“某张图片在每页重复出现”就盲目删除，因此比激进的重复-XObject启发式更不容易误删正文、Logo 或页眉。

## macOS：一次安装，以后点 Dock 图标

1. 下载/解压项目。
2. 双击 `install_mac.command`（首次可能需要右键 -> 打开）。
3. 脚本会在本机创建环境、打包 `.app`，并安装到 `~/Applications/PDF 水印清理.app`。
4. Finder 打开后，把 `PDF 水印清理.app` 拖到 Dock。
5. 以后直接点击 Dock 图标，或把 PDF 拖到 App 图标上。

输出例子：

`Homework.pdf` -> `Homework_clean.pdf`

如果同名文件已存在，会自动生成 `_clean_2`、`_clean_3`，不会覆盖。

## 开发运行

双击 `run_dev.command`，或者：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## 技术栈

- PyMuPDF: PDF 内容流读取/重写
- PyQt6: macOS GUI + drag & drop
- PyInstaller: 打包为 `.app`

## 隐私

所有处理均在本地完成，没有网络请求。

## 当前限制

如果水印已经被“烙”进扫描图片像素里，而不是独立的 PDF watermark object，本工具不会做图像修复式去水印，因为那很容易损伤手写内容。后续可以单独增加一个可选的“图像水印模式”。

## License

MIT

## GitHub Actions 自动构建 macOS App

仓库包含 `.github/workflows/build-macos.yml`。推送到 `main` 后，Actions 会在真实 macOS runner 上打包 `.app`，生成可下载的 `PDF-Watermark-Cleaner-macOS.zip` artifact。这样不需要把编译好的二进制提交进仓库。
