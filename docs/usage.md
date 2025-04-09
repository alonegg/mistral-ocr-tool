# 使用指南

## 命令行参数

| 参数 | 简写 | 描述 |
|------|------|------|
| `file_path` | - | PDF 或图像文件路径 |
| `--output` | `-o` | 输出文件路径 |
| `--api-key` | `-k` | Mistral AI API 密钥 |
| `--split` | `-s` | 在处理前将大型 PDF 拆分为块 |
| `--chunks` | `-c` | 将 PDF 拆分为的块数（默认：100） |
| `--model` | `-m` | 使用的 Mistral OCR 模型（默认：mistral-ocr-latest） |
| `--structured` | `-j` | 从 OCR 结果中提取结构化数据 |
| `--structured-model` | `-sm` | 用于结构化数据提取的模型（默认：pixtral-12b-latest） |
| `--max-retries` | `-r` | API 调用的最大重试次数（默认：3） |
| `--retry-delay` | `-d` | 重试之间的初始延迟（秒）（默认：2.0） |

## 示例

### 基本 PDF 处理

```bash
python mistral.py document.pdf