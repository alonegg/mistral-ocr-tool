import os
import base64
import json
import argparse
import math
import time
import functools
from pathlib import Path
from typing import Callable, Any, TypeVar
from PyPDF2 import PdfReader, PdfWriter
from mistralai import Mistral, DocumentURLChunk, ImageURLChunk, TextChunk
from mistralai.models import OCRResponse
try:
    from mistralai.exceptions import MistralAPIException
except ImportError:
    class MistralAPIException(Exception):
        def __init__(self, message=None, status_code=None):
            self.message = message
            self.status_code = status_code
            super().__init__(message)

# 定义一个类型变量用于装饰器
T = TypeVar('T')

def retry_on_error(max_retries: int = 3, initial_delay: float = 1.0, backoff_factor: float = 2.0, 
                  retry_on_exceptions=(MistralAPIException, ConnectionError)):
    """装饰器：在遇到特定异常时自动重试函数
    
    Args:
        max_retries: 最大重试次数
        initial_delay: 初始延迟时间（秒）
        backoff_factor: 退避因子，每次重试后延迟时间会乘以这个因子
        retry_on_exceptions: 需要重试的异常类型
    
    Returns:
        装饰后的函数
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None
            
            for retry in range(max_retries + 1):  # +1 是因为第一次不算重试
                try:
                    if retry > 0:
                        print(f"重试 {retry}/{max_retries}...")
                    return func(*args, **kwargs)
                except retry_on_exceptions as e:
                    last_exception = e
                    # 检查是否是502错误
                    if hasattr(e, 'status_code') and e.status_code == 502:
                        print(f"遇到502错误：服务器暂时不可用。正在重试...")
                    else:
                        print(f"遇到错误：{str(e)}。正在重试...")
                    
                    if retry < max_retries:
                        print(f"等待 {delay:.1f} 秒后重试...")
                        time.sleep(delay)
                        delay *= backoff_factor  # 指数退避
                    else:
                        print(f"已达到最大重试次数 ({max_retries})。操作失败。")
                        raise last_exception
            
            # 这行代码理论上不会执行，但为了类型检查添加
            raise last_exception
        
        return wrapper
    return decorator

def read_pdf_as_base64(pdf_path):
    """Read a PDF file and encode it as base64."""
    with open(pdf_path, 'rb') as file:
        return base64.b64encode(file.read()).decode('utf-8')

def get_combined_markdown(ocr_response: OCRResponse) -> str:
    """
    Combine OCR text and images into a single markdown document.

    Args:
        ocr_response: Response from OCR processing containing text and images

    Returns:
        Combined markdown string with embedded images
    """
    markdowns = []
    # Extract images from page
    for page in ocr_response.pages:
        # Get markdown content from page
        markdowns.append(page.markdown)

    return "\n\n".join(markdowns)

@retry_on_error(max_retries=3, initial_delay=2.0)
def upload_file_to_ocr_service(client, file_path):
    """上传文件到Mistral OCR服务，并返回签名URL
    
    Args:
        client: Mistral客户端实例
        file_path: 文件路径对象
        
    Returns:
        签名URL对象
    """
    print(f"Uploading {file_path.name} to Mistral AI OCR service...")
    try:
        uploaded_file = client.files.upload(
            file={
                "file_name": file_path.stem,
                "content": file_path.read_bytes(),
            },
            purpose="ocr",
        )
        
        # 获取上传文件的URL
        return client.files.get_signed_url(file_id=uploaded_file.id, expiry=1)
    except MistralAPIException as e:
        if hasattr(e, 'status_code'):
            if e.status_code == 502:
                print(f"Error 502: 服务器暂时不可用。这可能是由于服务器负载过高或维护。")
            elif e.status_code == 413:
                print(f"Error 413: 文件太大。请尝试拆分PDF或减小文件大小。")
            elif e.status_code == 429:
                print(f"Error 429: 请求过多。请稍后再试。")
            else:
                print(f"API错误: {e.status_code} - {str(e)}")
        raise

@retry_on_error(max_retries=3, initial_delay=2.0)
def process_with_ocr(client, document_url, model):
    """使用OCR处理文档
    
    Args:
        client: Mistral客户端实例
        document_url: 文档URL
        model: 使用的模型名称
        
    Returns:
        OCR处理结果
    """
    print(f"Processing document with Mistral OCR...")
    return client.ocr.process(
        document=DocumentURLChunk(document_url=document_url),
        model=model,
        include_image_base64=False
    )

def convert_pdf_to_markdown(api_key, pdf_path, output_path=None, model="mistral-ocr-latest"):
    """Convert a PDF file to Markdown using Mistral AI OCR API."""
    # Check if the file exists
    if not os.path.exists(pdf_path):
        print(f"Error: File {pdf_path} does not exist.")
        return
    
    try:
        # Initialize Mistral client with API key
        client = Mistral(api_key=api_key)
        
        # Convert path to Path object
        pdf_file = Path(pdf_path)
        
        # 使用重试机制上传文件
        try:
            signed_url = upload_file_to_ocr_service(client, pdf_file)
        except Exception as e:
            print(f"上传文件失败: {str(e)}")
            print("提示: 请检查您的网络连接和API密钥是否正确。如果问题持续存在，请联系Mistral AI支持。")
            return None
        
        # 使用重试机制处理PDF
        try:
            print(f"Processing {pdf_file.name} with Mistral OCR...")
            pdf_response = process_with_ocr(client, signed_url.url, model)
        except Exception as e:
            print(f"处理PDF失败: {str(e)}")
            print("提示: 如果PDF文件很大，请考虑使用--split选项将其拆分为较小的块。")
            return None
        
        # Get combined markdown from OCR response
        markdown_content = get_combined_markdown(pdf_response)
        
        # Determine output path
        if not output_path:
            output_path = os.path.splitext(pdf_path)[0] + ".md"
        
        # Save the markdown content
        with open(output_path, "w", encoding="utf-8") as md_file:
            md_file.write(markdown_content)
        
        print(f"Conversion successful! Markdown saved to {output_path}")
        
        # Convert response to JSON for usage info
        response_dict = json.loads(pdf_response.model_dump_json())
        if "usage_info" in response_dict:
            usage = response_dict["usage_info"]
            print(f"Pages processed: {usage.get('pages_processed', 'N/A')}")
            print(f"Document size: {usage.get('doc_size_bytes', 'N/A')} bytes")
        
        return output_path
    
    except Exception as e:
        print(f"Error: {str(e)}")
        print("如果您遇到网络问题或服务器错误，请稍后再试。")
        return None

@retry_on_error(max_retries=3, initial_delay=2.0)
def process_image_with_ocr(client, image_url, model):
    """使用OCR处理图像
    
    Args:
        client: Mistral客户端实例
        image_url: 图像URL
        model: 使用的模型名称
        
    Returns:
        OCR处理结果
    """
    print(f"Processing image with Mistral OCR...")
    return client.ocr.process(
        document=ImageURLChunk(image_url=image_url),
        model=model
    )

def convert_image_to_markdown(api_key, image_path, output_path=None, model="mistral-ocr-latest"):
    """Convert an image file to Markdown using Mistral AI OCR API."""
    # Check if the file exists
    if not os.path.exists(image_path):
        print(f"Error: File {image_path} does not exist.")
        return
    
    try:
        # Initialize Mistral client with API key
        client = Mistral(api_key=api_key)
        
        # Convert path to Path object
        image_file = Path(image_path)
        
        # Read and encode the image file
        print(f"Processing {image_file.name} with Mistral OCR...")
        encoded = base64.b64encode(image_file.read_bytes()).decode()
        base64_data_url = f"data:image/jpeg;base64,{encoded}"
        
        # 使用重试机制处理图像
        try:
            image_response = process_image_with_ocr(client, base64_data_url, model)
        except Exception as e:
            print(f"处理图像失败: {str(e)}")
            print("提示: 请检查图像格式是否支持，或尝试转换为其他格式。")
            return None
        
        # Get combined markdown from OCR response
        markdown_content = get_combined_markdown(image_response)
        
        # Determine output path
        if not output_path:
            output_path = os.path.splitext(image_path)[0] + ".md"
        
        # Save the markdown content
        with open(output_path, "w", encoding="utf-8") as md_file:
            md_file.write(markdown_content)
        
        print(f"Conversion successful! Markdown saved to {output_path}")
        
        # Convert response to JSON for usage info
        response_dict = json.loads(image_response.model_dump_json())
        if "usage_info" in response_dict:
            usage = response_dict["usage_info"]
            print(f"Pages processed: {usage.get('pages_processed', 'N/A')}")
        
        return output_path
    
    except Exception as e:
        print(f"Error: {str(e)}")
        print("如果您遇到网络问题或服务器错误，请稍后再试。")
        return None

def split_pdf(pdf_path, output_dir=None, num_chunks=100):
    """Split a PDF file into multiple smaller PDF files."""
    # Create output directory if it doesn't exist
    if not output_dir:
        output_dir = os.path.join(os.path.dirname(pdf_path), "split_pdfs")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Get the base filename without extension
    base_filename = os.path.splitext(os.path.basename(pdf_path))[0]
    
    # Read the PDF
    pdf = PdfReader(pdf_path)
    total_pages = len(pdf.pages)
    
    # Calculate pages per chunk (at least 1 page per chunk)
    pages_per_chunk = max(1, math.ceil(total_pages / num_chunks))
    
    # Calculate actual number of chunks needed
    actual_chunks = math.ceil(total_pages / pages_per_chunk)
    
    print(f"Splitting {pdf_path} into {actual_chunks} chunks with approximately {pages_per_chunk} pages per chunk...")
    
    chunk_paths = []
    
    # Split the PDF into chunks
    for i in range(actual_chunks):
        start_page = i * pages_per_chunk
        end_page = min((i + 1) * pages_per_chunk, total_pages)
        
        # Create a new PDF writer
        pdf_writer = PdfWriter()
        
        # Add pages to the writer
        for page_num in range(start_page, end_page):
            pdf_writer.add_page(pdf.pages[page_num])
        
        # Save the chunk
        output_path = os.path.join(output_dir, f"{base_filename}_chunk_{i+1:03d}.pdf")
        with open(output_path, "wb") as output_file:
            pdf_writer.write(output_file)
        
        chunk_paths.append(output_path)
        
    print(f"Successfully split PDF into {len(chunk_paths)} chunks in {output_dir}")
    return chunk_paths

@retry_on_error(max_retries=3, initial_delay=2.0)
def chat_complete_with_retry(client, model, messages, response_format=None, temperature=0):
    """使用重试机制调用聊天完成API
    
    Args:
        client: Mistral客户端实例
        model: 使用的模型名称
        messages: 消息列表
        response_format: 响应格式
        temperature: 温度参数
        
    Returns:
        聊天完成结果
    """
    print(f"Calling model {model} for structured data extraction...")
    return client.chat.complete(
        model=model,
        messages=messages,
        response_format=response_format or {"type": "json_object"},
        temperature=temperature,
    )

def extract_structured_data(api_key, file_path, model="pixtral-12b-latest", output_path=None):
    """Extract structured data from OCR results using a model."""
    # Check if the file exists
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} does not exist.")
        return
    
    try:
        # Initialize Mistral client with API key
        client = Mistral(api_key=api_key)
        
        # Check if the file is an image or a PDF
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext in [".jpg", ".jpeg", ".png"]:
            # Process image
            image_file = Path(file_path)
            encoded = base64.b64encode(image_file.read_bytes()).decode()
            base64_data_url = f"data:image/jpeg;base64,{encoded}"
            
            # 使用重试机制处理图像
            try:
                image_response = process_image_with_ocr(client, base64_data_url, "mistral-ocr-latest")
                # Get OCR markdown
                image_ocr_markdown = image_response.pages[0].markdown
            except Exception as e:
                print(f"处理图像失败: {str(e)}")
                print("提示: 请检查图像格式是否支持，或尝试转换为其他格式。")
                return None
            
            # 使用重试机制获取结构化响应
            try:
                chat_response = chat_complete_with_retry(
                    client,
                    model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                ImageURLChunk(image_url=base64_data_url),
                                TextChunk(
                                    text=(
                                        f"This is image's OCR in markdown:\n\n{image_ocr_markdown}\n.\n"
                                        "Convert this into a sensible structured json response. "
                                        "The output should be strictly be json with no extra commentary"
                                    )
                                ),
                            ],
                        }
                    ],
                    response_format={"type": "json_object"},
                    temperature=0,
                )
                
                # Parse JSON response
                structured_data = json.loads(chat_response.choices[0].message.content)
            except Exception as e:
                print(f"提取结构化数据失败: {str(e)}")
                print("提示: 请检查模型是否可用，或尝试使用不同的模型。")
                return None
            
        elif file_ext == ".pdf":
            # For PDF, first convert to markdown, then process
            md_path = convert_pdf_to_markdown(api_key, file_path)
            
            if not md_path:
                print("Error: Failed to convert PDF to markdown.")
                return
            
            # Read the markdown content
            with open(md_path, "r", encoding="utf-8") as md_file:
                markdown_content = md_file.read()
            
            # 使用重试机制获取结构化响应
            try:
                chat_response = chat_complete_with_retry(
                    client,
                    model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                TextChunk(
                                    text=(
                                        f"This is document's OCR in markdown:\n\n{markdown_content}\n.\n"
                                        "Convert this into a sensible structured json response. "
                                        "The output should be strictly be json with no extra commentary"
                                    )
                                ),
                            ],
                        }
                    ],
                    response_format={"type": "json_object"},
                    temperature=0,
                )
                
                # Parse JSON response
                structured_data = json.loads(chat_response.choices[0].message.content)
            except Exception as e:
                print(f"提取结构化数据失败: {str(e)}")
                print("提示: 请检查模型是否可用，或尝试使用不同的模型。")
                return None
        else:
            print(f"Error: Unsupported file format: {file_ext}")
            return
        
        # Save structured data to file if output path is provided
        if output_path:
            with open(output_path, "w", encoding="utf-8") as json_file:
                json.dump(structured_data, json_file, indent=4)
            print(f"Structured data saved to {output_path}")
        else:
            # Print structured data
            print(json.dumps(structured_data, indent=4))
        
        return structured_data
    
    except Exception as e:
        print(f"Error: {str(e)}")
        print("如果您遇到网络问题或服务器错误，请稍后再试。")
        return None

def process_pdf_in_chunks(api_key, pdf_path, output_path=None, num_chunks=100, model="mistral-ocr-latest"):
    """Process a large PDF by splitting it into chunks and processing each chunk."""
    # Split the PDF into chunks
    try:
        chunk_paths = split_pdf(pdf_path, num_chunks=num_chunks)
    except Exception as e:
        print(f"拆分PDF失败: {str(e)}")
        print("提示: 请确保PDF文件未损坏且可读取。")
        return None
    
    # Process each chunk
    chunk_outputs = []
    failed_chunks = []
    
    for i, chunk_path in enumerate(chunk_paths):
        print(f"Processing chunk {i+1}/{len(chunk_paths)}: {os.path.basename(chunk_path)}")
        
        # Generate output path for this chunk if not provided
        chunk_output_path = None
        if output_path:
            chunk_output_dir = os.path.join(os.path.dirname(output_path), "chunk_outputs")
            if not os.path.exists(chunk_output_dir):
                os.makedirs(chunk_output_dir)
            chunk_output_path = os.path.join(chunk_output_dir, f"{os.path.splitext(os.path.basename(chunk_path))[0]}.md")
        
        # Process the chunk with retry
        max_chunk_retries = 2
        for retry in range(max_chunk_retries + 1):
            try:
                # Process the chunk
                result_path = convert_pdf_to_markdown(api_key, chunk_path, chunk_output_path, model)
                if result_path:
                    chunk_outputs.append(result_path)
                    break
                else:
                    if retry < max_chunk_retries:
                        print(f"处理块 {i+1} 失败，正在重试 ({retry+1}/{max_chunk_retries})...")
                        time.sleep(2 * (retry + 1))  # 增加延迟
                    else:
                        print(f"处理块 {i+1} 失败，跳过此块。")
                        failed_chunks.append(i+1)
            except Exception as e:
                if retry < max_chunk_retries:
                    print(f"处理块 {i+1} 时出错: {str(e)}，正在重试 ({retry+1}/{max_chunk_retries})...")
                    time.sleep(2 * (retry + 1))  # 增加延迟
                else:
                    print(f"处理块 {i+1} 失败，跳过此块: {str(e)}")
                    failed_chunks.append(i+1)
    
    # Combine all chunk outputs into a single file if output_path is provided
    if output_path and chunk_outputs:
        print(f"Combining {len(chunk_outputs)} chunk outputs into {output_path}...")
        with open(output_path, "w", encoding="utf-8") as combined_file:
            for chunk_output in chunk_outputs:
                with open(chunk_output, "r", encoding="utf-8") as chunk_file:
                    combined_file.write(chunk_file.read())
                    combined_file.write("\n\n")
        
        print(f"Successfully combined all chunks into {output_path}")
        
        # 报告失败的块
        if failed_chunks:
            print(f"警告: {len(failed_chunks)} 个块处理失败: {failed_chunks}")
            print("最终输出文件可能不完整。")
        
        return output_path
    
    # 如果没有成功处理任何块，则返回None
    if not chunk_outputs:
        print("错误: 所有块处理失败。")
        return None
    
    # 报告失败的块
    if failed_chunks:
        print(f"警告: {len(failed_chunks)} 个块处理失败: {failed_chunks}")
        print("部分内容可能丢失。")
    
    return chunk_outputs

def main():
    parser = argparse.ArgumentParser(description="Convert PDF or image to Markdown using Mistral AI OCR API")
    parser.add_argument("file_path", help="Path to the PDF or image file")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--api-key", "-k", help="Mistral AI API key")
    parser.add_argument("--split", "-s", action="store_true", help="Split large PDF into chunks before processing")
    parser.add_argument("--chunks", "-c", type=int, default=100, help="Number of chunks to split the PDF into (default: 100)")
    parser.add_argument("--model", "-m", default="mistral-ocr-latest", help="Mistral OCR model to use (default: mistral-ocr-latest)")
    parser.add_argument("--structured", "-j", action="store_true", help="Extract structured data from OCR results")
    parser.add_argument("--structured-model", "-sm", default="pixtral-12b-latest", help="Model to use for structured data extraction (default: pixtral-12b-latest)")
    parser.add_argument("--max-retries", "-r", type=int, default=3, help="Maximum number of retries for API calls (default: 3)")
    parser.add_argument("--retry-delay", "-d", type=float, default=2.0, help="Initial delay between retries in seconds (default: 2.0)")
    
    args = parser.parse_args()
    
    # Get API key from arguments or environment variable
    api_key = args.api_key or os.getenv("MISTRAL_API_KEY")
    
    if not api_key:
        print("Error: Mistral AI API key is required. Provide it with --api-key or set the MISTRAL_API_KEY environment variable.")
        return
    
    # 检查文件是否存在
    if not os.path.exists(args.file_path):
        print(f"Error: File {args.file_path} does not exist.")
        return
    
    # 检查文件扩展名
    file_ext = os.path.splitext(args.file_path)[1].lower()
    
    # 确定输出路径（如果未提供）
    output_path = args.output
    if not output_path:
        if args.structured:
            output_path = os.path.splitext(args.file_path)[0] + ".json"
        else:
            output_path = os.path.splitext(args.file_path)[0] + ".md"
    
    # 根据文件类型和选项处理文件
    try:
        result = None
        if file_ext == ".pdf":
            print(f"处理PDF文件: {args.file_path}")
            if args.structured:
                result = extract_structured_data(api_key, args.file_path, args.structured_model, output_path)
            elif args.split:
                print(f"将PDF拆分为最多{args.chunks}个块进行处理...")
                result = process_pdf_in_chunks(api_key, args.file_path, output_path, args.chunks, args.model)
            else:
                result = convert_pdf_to_markdown(api_key, args.file_path, output_path, args.model)
        elif file_ext in [".jpg", ".jpeg", ".png"]:
            print(f"处理图像文件: {args.file_path}")
            if args.structured:
                result = extract_structured_data(api_key, args.file_path, args.structured_model, output_path)
            else:
                result = convert_image_to_markdown(api_key, args.file_path, output_path, args.model)
        else:
            print(f"Error: 不支持的文件格式: {file_ext}")
            print("支持的格式: .pdf, .jpg, .jpeg, .png")
            return
        
        # 检查处理结果
        if result:
            print("\n处理完成!")
            if isinstance(result, str):
                print(f"输出保存到: {result}")
            elif isinstance(result, list) and result:
                print(f"输出保存到多个文件，第一个文件: {result[0]}")
        else:
            print("\n处理失败。请查看上面的错误信息。")
            print("\n故障排除提示:")
            print("1. 如果遇到502错误，这通常是临时性服务器问题，请稍后重试。")
            print("2. 对于大型PDF文件，请使用--split选项将其拆分为较小的块。")
            print("3. 检查您的网络连接是否稳定。")
            print("4. 确保您的API密钥有效且未过期。")
    except KeyboardInterrupt:
        print("\n操作被用户中断。")
    except Exception as e:
        print(f"\n发生意外错误: {str(e)}")
        print("\n如果问题持续存在，请联系支持团队或在GitHub上提交问题。")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()