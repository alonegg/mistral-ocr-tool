# Mistral PDF/OCR 工具使用指南

## 1. 命令行参数

| 参数 | 简写 | 类型 | 默认值 | 描述 |
|------|------|------|------|------|
| `file_path` | - | string | 必填 | PDF或图像文件路径 |
| `--output`, `-o` | `-o` | string | 自动生成 | 输出文件路径 |
| `--api-key`, `-k` | `-k` | string | 必填 | Mistral AI API密钥 |
| `--split`, `-s` | `-s` | flag | false | 在处理前将大型PDF拆分为块 |
| `--chunks`, `-c` | `-c` | int | 100 | 将PDF拆分为的块数 |
| `--model`, `-m` | `-m` | string | mistral-ocr-latest | 使用的Mistral OCR模型 |
| `--structured`, `-j` | `-j` | flag | false | 从OCR结果中提取结构化数据 |
| `--structured-model`, `-sm` | `-sm` | string | pixtral-12b-latest | 用于结构化数据提取的模型 |
| `--max-retries`, `-r` | `-r` | int | 3 | API调用的最大重试次数 |
| `--retry-delay`, `-d` | `-d` | float | 2.0 | 重试之间的初始延迟(秒) |

## 2. 使用示例

### 2.1 基本用法

```bash
# 处理PDF文件
python mistral.py document.pdf

# 处理图像文件
python mistral.py image.jpg

# 指定输出文件路径
python mistral.py document.pdf --output result.md
```

### 2.2 高级用法

```bash
# 拆分大型PDF文件(拆分为50个块)
python mistral.py large_document.pdf --split --chunks 50

# 提取结构化数据并保存为JSON
python mistral.py document.pdf --structured --output data.json

# 使用特定模型处理文件
python mistral.py document.pdf --model mistral-ocr-latest

# 设置API密钥和重试参数
python mistral.py document.pdf --api-key YOUR_API_KEY --max-retries 5 --retry-delay 3.0
```

## 3. 故障排除
### 3.1 常见错误及解决方案

| 错误类型 | 可能原因 | 解决方案 |
|---------|---------|---------|
| API密钥错误 | 密钥无效或过期 | 检查密钥是否正确，或申请新密钥 |
| 502错误 | 服务器暂时不可用 | 等待几分钟后重试，或联系Mistral支持 |
| 大型文件处理失败 | 文件过大或内存不足 | 使用`--split`选项拆分文件，或增加`--chunks`值 |
| 网络问题 | 连接不稳定或超时 | 检查网络连接，或增加`--max-retries`和`--retry-delay` |
| 模型不可用 | 指定模型不存在 | 检查模型名称拼写，或使用默认模型 |

### 3.2 日志和调试信息
程序会输出以下信息帮助诊断问题：

- **上传进度**：文件上传百分比和速度
- **处理状态**：当前处理阶段和预计剩余时间
- **错误详情**：完整的错误消息和堆栈跟踪
- **重试记录**：重试次数和下次重试时间
- **资源使用**：内存、CPU和网络使用情况

### 3.3 最佳实践建议
1. 对于大于100MB的文件，始终使用`--split`选项
2. 处理重要文档时，先测试小样本
3. 定期检查API密钥有效期
4. 网络不稳定时增加重试参数
5. 使用`--output`指定输出路径避免数据丢失


### 5. 创建示例文件

```markdown:%2Fhome%2Fubuntu%2Fpdf%2Fexamples%2Fbasic_usage.md
# 基本用法示例

## 处理 PDF 文件

```bash
python mistral.py sample.pdf

Processing sample.pdf with Mistral OCR...
Conversion successful! Markdown saved to sample.md
Pages processed: 5
Document size: 1245678 bytes

处理完成!
输出保存到: sample.md

## 处理图像文件
```bash
python mistral.py image.jpg
 ```Processing image.jpg with Mistral OCR...
Conversion successful! Markdown saved to image.md

处理完成!
输出保存到: image.md

```markdown:%2Fhome%2Fubuntu%2Fpdf%2Fexamples%2Fadvanced_usage.md
# 高级用法示例

## 拆分大型 PDF 处理

```bash
python mistral.py large_document.pdf --split --chunks 20

输出：

```plaintext
将PDF拆分为最多20个块进行处理...
Splitting large_document.pdf into 20 chunks with approximately 5 pages per chunk...
Successfully split PDF into 20 chunks in /home/user/split_pdfs
Processing chunk 1/20: large_document_chunk_001.pdf
...
Successfully combined all chunks into large_document.md

处理完成!
输出保存到: large_document.md
 ```
```

## 提取结构化数据
```bash
```
python mistral.py document.pdf --structured --output document.json

输出：

```plaintext
处理PDF文件: document.pdf
Calling model pixtral-12b-latest for structured data extraction...
Structured data saved to document.json

处理完成!
输出保存到: document.json
 ```
```

