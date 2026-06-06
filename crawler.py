import requests
from bs4 import BeautifulSoup
import re
import math
import logging
from collections import Counter

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

REQUEST_TIMEOUT = 15

# 中文停用词
STOP_WORDS = set(
    '的 了 在 是 我 有 和 就 不 人 都 一 一个 上 也 很 到 说 要 去 你 会 着 没有 看 好 '
    '自己 这 他 她 它 们 那 里 为 什么 没 被 从 可以 这个 那个 但 而 与 又 或 如果 '
    '因为 所以 虽然 但是 可是 然后 不过 因此 之后 之前 已经 还是 只是 这样 那样 '
    '怎么 哪 谁 多 少 些 每 各 该 其 此 另 其中 通过 进行 以及 对于 关于 根据 '
    '目前 同时 并且 以及 由于 其中 以及 作为 不仅 而是'.split()
)


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


def _tokenize(text):
    """简单中文分词：按字符切分，过滤停用词和标点"""
    words = []
    # 提取中文字符和英文单词
    tokens = re.findall(r'[\u4e00-\u9fff]|[a-zA-Z]+', text)
    for t in tokens:
        t_lower = t.lower()
        if t_lower not in STOP_WORDS and len(t_lower) > 0:
            words.append(t_lower)
    return words


def _summarize(paragraphs, max_length=200):
    """基于关键词权重的全文摘要：通读全文后提取最能概括主旨的句子"""
    # 将所有段落合并为全文
    full_text = ' '.join(paragraphs)

    # 分句：按中英文句末标点切分
    raw_sentences = re.split(r'[。！？!?]', full_text)
    sentences = []
    for s in raw_sentences:
        s = s.strip()
        # 过滤太短的句子和无关内容
        if s and len(s) > 8 and not re.match(
                r'^(版权|声明|转载|关注|扫码|下载|点击|阅读原文|责任编辑|编辑|来源|免责)',
                s):
            sentences.append(s)

    if not sentences:
        if paragraphs:
            return _truncate(paragraphs[0], max_length)
        return ''

    if len(sentences) <= 3:
        # 短文直接拼接
        result = '。'.join(sentences)
        return _truncate(result, max_length)

    # 第一步：计算全文关键词词频（TF）
    all_words = _tokenize(full_text)
    word_freq = Counter(all_words)

    # 去掉频率过高（出现在超过80%句子中的词）和过低的词
    total_words = sum(word_freq.values())
    filtered_freq = {}
    for word, freq in word_freq.items():
        ratio = freq / total_words if total_words > 0 else 0
        if 0.0005 < ratio < 0.1:
            filtered_freq[word] = freq

    # 第二步：为每个句子打分
    sentence_scores = []
    for idx, sent in enumerate(sentences):
        score = 0.0
        words = _tokenize(sent)

        # 关键词匹配得分：句子中包含的关键词权重之和
        for w in words:
            if w in filtered_freq:
                score += filtered_freq[w]

        # 位置权重：首尾段落更重要
        position = idx / len(sentences)
        if position < 0.15:
            score *= 1.5  # 开头部分加权
        elif position > 0.85:
            score *= 1.2  # 结尾部分加权

        # 长度偏好：过短的句子信息量不足
        if len(sent) < 15:
            score *= 0.5

        # 归一化：按句子长度归一，避免长句天然得分高
        if len(words) > 0:
            score = score / math.sqrt(len(words))

        sentence_scores.append((idx, score))

    # 第三步：按得分排序，选取最重要的句子
    sentence_scores.sort(key=lambda x: x[1], reverse=True)

    # 选取top句子，控制总长度
    selected_indices = []
    total_len = 0
    for idx, score in sentence_scores:
        sent = sentences[idx]
        if total_len + len(sent) + 1 > max_length:
            continue
        if idx not in selected_indices:
            selected_indices.append(idx)
            total_len += len(sent) + 1
        if total_len >= max_length * 0.8:
            break

    # 至少选2句，最多5句
    if len(selected_indices) < 2 and len(sentences) >= 2:
        for idx, _ in sentence_scores:
            if idx not in selected_indices:
                selected_indices.append(idx)
                break
    if len(selected_indices) > 5:
        selected_indices = selected_indices[:5]

    # 第四步：按原文顺序排列，保证逻辑连贯
    selected_indices.sort()

    result = '。'.join(sentences[i] for i in selected_indices)
    if not result.endswith(('。', '！', '？', '.', '!', '?')):
        result += '。'
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
