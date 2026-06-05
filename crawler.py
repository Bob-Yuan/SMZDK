import requests
from bs4 import BeautifulSoup
import re
import logging

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

REQUEST_TIMEOUT = 15


def fetch_article(url):
    """抓取文章链接，返回标题和内容梗概"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT,
                            allow_redirects=True)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or 'utf-8'
    except requests.RequestException as e:
        logger.warning('抓取链接失败: %s, 错误: %s', url, e)
        return '', ''

    soup = BeautifulSoup(resp.text, 'html.parser')

    # 移除不需要的标签
    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside',
                     'iframe', 'noscript']):
        tag.decompose()

    # 获取标题
    title = ''
    if soup.find('h1'):
        title = soup.find('h1').get_text(strip=True)
    elif soup.find('title'):
        title = soup.find('title').get_text(strip=True)

    # 优先从 meta description 获取摘要
    meta_desc = ''
    meta_tag = soup.find('meta', attrs={'name': 'description'})
    if meta_tag and meta_tag.get('content'):
        meta_desc = meta_tag['content'].strip()

    # 提取正文段落
    paragraphs = []

    # 优先查找 article 标签
    article = soup.find('article')
    if article:
        for p in article.find_all(['p', 'h2', 'h3', 'h4']):
            text = p.get_text(strip=True)
            if text and len(text) > 10:
                paragraphs.append(text)
    else:
        # 查找主要内容区域
        content_tags = soup.find_all(['p', 'h2', 'h3'])
        for tag in content_tags:
            text = tag.get_text(strip=True)
            if text and len(text) > 10:
                paragraphs.append(text)

    # 生成梗概
    if paragraphs:
        summary = _summarize(paragraphs, max_length=200)
    elif meta_desc:
        summary = _truncate(meta_desc, 200)
    else:
        summary = '无法自动获取内容梗概。'

    return title, summary


def _summarize(paragraphs, max_length=200):
    """从段落列表中提取关键句，生成精炼梗概"""
    # 筛选有实质内容的句子
    sentences = []
    for p in paragraphs:
        # 按中英文句号、问号、感叹号分句
        parts = re.split(r'[。！？；!?;]', p)
        for s in parts:
            s = s.strip()
            # 过滤太短的句子和导航/版权等无关内容
            if s and len(s) > 8 and not re.match(r'^(版权|声明|转载|关注|扫码|下载|点击|阅读原文)', s):
                sentences.append(s)

    if not sentences:
        # 退而求其次，取第一段截断
        if paragraphs:
            return _truncate(paragraphs[0], max_length)
        return ''

    # 选取关键句：首句必选，然后按位置权重选取
    selected = [sentences[0]]
    total_len = len(sentences[0])

    # 从剩余句子中按间隔选取，直到接近 max_length
    step = max(1, len(sentences) // 5)  # 均匀采样
    for i in range(step, len(sentences), step):
        s = sentences[i]
        if total_len + len(s) + 1 > max_length:
            break
        selected.append(s)
        total_len += len(s) + 1

    result = '。'.join(selected)
    if not result.endswith(('。', '！', '？', '.', '!', '?')):
        result += '…'
    return result


def _truncate(text, max_length=200):
    """截断文本到指定长度，按句子断开"""
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) <= max_length:
        return text
    truncated = text[:max_length]
    for sep in ['。', '！', '？', '.', '！', '?', '；', ';']:
        last_pos = truncated.rfind(sep)
        if last_pos > max_length * 0.5:
            return text[:last_pos + 1] + '…'
    return truncated + '…'


def fetch_link_info(url, category):
    """根据分类获取链接信息"""
    if category == '文章':
        title, summary = fetch_article(url)
        return title, summary
    elif category == '视频':
        return '', '视频内容，请点击链接查看。'
    elif category == '图片':
        return '', '图片内容，请点击链接查看。'
    else:
        return '', ''
