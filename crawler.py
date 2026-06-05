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
    """抓取文章链接，返回标题和内容摘要"""
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

    # 尝试从 meta description 获取摘要
    meta_desc = ''
    meta_tag = soup.find('meta', attrs={'name': 'description'})
    if meta_tag and meta_tag.get('content'):
        meta_desc = meta_tag['content'].strip()

    # 提取正文内容
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

    # 生成摘要
    if paragraphs:
        content_text = '\n'.join(paragraphs[:10])
        summary = _summarize(content_text, max_length=500)
    elif meta_desc:
        summary = meta_desc
    else:
        summary = '无法自动获取内容摘要。'

    return title, summary


def _summarize(text, max_length=500):
    """简单摘要：提取前N个字符，按句子截断"""
    # 清理多余空白
    text = re.sub(r'\s+', ' ', text).strip()

    if len(text) <= max_length:
        return text

    # 在 max_length 附近找句号断句
    truncated = text[:max_length]
    for sep in ['。', '！', '？', '.', '！', '?', '；', ';']:
        last_pos = truncated.rfind(sep)
        if last_pos > max_length * 0.5:
            return text[:last_pos + 1] + '...'

    return truncated + '...'


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
