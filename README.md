# Mistral OCR 工具

这是一个使用 Mistral AI API 进行 OCR（光学字符识别）处理的工具，可以将 PDF 文档或图像转换为 Markdown 格式，并支持结构化数据提取。

## 功能特点

- PDF 文档转 Markdown
- 图像转 Markdown
- 大型 PDF 文件分块处理
- 结构化数据提取
- 自动重试机制
- 支持中英文处理

## 安装

```bash
git clone https://github.com/alonegg/mistral-ocr-tool.git
cd mistral-ocr-tool
pip install -r requirements.txt

## 使用方法
### 基本用法
```bash
python mistral.py your_file.pdf --api-key YOUR_API_KEY
 ```

或者设置环境变量：

```bash
export MISTRAL_API_KEY=your_api_key
python mistral.py your_file.pdf
 ```

### 处理大型 PDF
```bash
python mistral.py large_document.pdf --split --chunks 50
 ```

### 提取结构化数据
```bash
python mistral.py document.pdf --structured
 ```

### 更多选项
```bash
python mistral.py --help
 ```
## 获取MISTRAL_API_KEY
https://mistral.ai/。---> try the api

## 文档
详细文档请参阅 docs 目录。

## 许可证
MIT

## 贡献
欢迎提交 Pull Request 或创建 Issue！



