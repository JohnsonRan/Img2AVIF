# Img2AVIF

使用 `avifenc` 命令行工具实现真正的像素级无损转换，支持多线程处理。

## 功能特点

- ✅ 无损编码
- ✅ 遍历所有子目录
- ✅ 保留原始目录结构
- ✅ 支持多线程并发处理
- ✅ 支持多种图片格式：JPG, PNG, BMP, GIF, TIFF, WebP
- ✅ 转换完成后可选择删除原始文件
- ✅ 显示详细的转换进度、文件大小对比和统计信息

## 安装依赖

### 1. 安装 avifenc

**Windows:**
```bash
scoop install libavif
```

或从 [GitHub Releases](https://github.com/AOMediaCodec/libavif/releases) 下载并添加到 PATH

**Linux:**
```bash
sudo apt install libavif-bin  # Ubuntu/Debian
# 或
sudo dnf install libavif-tools  # Fedora
```

**macOS:**
```bash
brew install libavif
```

## 使用方法

### 交互式运行

```bash
python convert_to_avif.py
```

按提示输入：
- 目标目录路径（留空使用当前目录）
- 线程数（留空使用默认值8）

### 示例

```bash
# 转换当前目录下的所有图片
python convert_to_avif.py

# 转换指定目录
python convert_to_avif.py Photos
```