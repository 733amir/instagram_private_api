import time
import hmac
import base64
import hashlib
from random import randint
import os
from datetime import datetime
import re


VALID_UUID_RE = r'^[a-f\d]{8}\-[a-f\d]{4}\-[a-f\d]{4}-[a-f\d]{4}-[a-f\d]{12}$'


def raise_if_invalid_rank_token(val, required=True):
    if required and not val:
        raise ValueError('rank_token is required')
    if not re.match(VALID_UUID_RE, val):
        raise ValueError('Invalid rank_token: {}'.format(val))


def gen_user_breadcrumb(size):
    """
    Used in comments posting.

    :param size:
    :return:
    """
    key = 'iN4$aGr0m'
    dt = int(time.time() * 1000)

    # typing time elapsed
    time_elapsed = randint(500, 1500) + size * randint(500, 1500)

    text_change_event_count = max(1, size / randint(3, 5))

    data = '{size!s} {elapsed!s} {count!s} {dt!s}'.format(**{
        'size': size, 'elapsed': time_elapsed, 'count': text_change_event_count, 'dt': dt
    })
    return '{0!s}\n{1!s}\n'.format(
        base64.b64encode(hmac.new(key.encode('ascii'), data.encode('ascii'), digestmod=hashlib.sha256).digest()),
        base64.b64encode(data.encode('ascii')))


class Chunk(object):
    """
    Simple object class to encapulate an upload Chunk
    """
    def __init__(self, index, start, end, total):
        self.index = index
        self.start = start
        self.end = end
        self.total = total

    @property
    def is_first(self):
        return self.index == 0

    @property
    def is_last(self):
        return self.index == self.total - 1

    @property
    def length(self):
        return self.end - self.start


def get_file_size(fp):
    """
    Get the file size for a file-like object

    :param fp: file-like object
    :return:
    """
    original_file_position = fp.tell()
    fp.seek(0, os.SEEK_END)
    file_len = fp.tell()
    fp.seek(original_file_position, os.SEEK_SET)
    return file_len


def chunk_generator(chunk_count, chunk_size, file_data):
    """
    Generic chunk generator logic

    :param chunk_count: Number of chunks wanted
    :param chunk_size: Size of each chunk
    :param file_data: bytes to be split into chunk
    :return:
    """
    try:
        total_len = len(file_data)
        is_fp = False
    except TypeError:
        total_len = get_file_size(file_data)
        is_fp = True
    for i in range(chunk_count):
        start_range = i * chunk_size
        end_range = (start_range + chunk_size) if i < (chunk_count - 1) else total_len
        chunk_info = Chunk(i, start_range, end_range, chunk_count)
        if is_fp:
            file_data.seek(chunk_info.start, os.SEEK_SET)
            yield chunk_info, file_data.read(chunk_info.length)
        else:
            yield chunk_info, file_data[chunk_info.start: chunk_info.end]


def max_chunk_size_generator(chunk_size, file_data):
    """
    Generate chunks by defining a maximum chunk size

    :param chunk_size: Maximum chunk size allow
    :param file_data: bytes data
    :return:
    """
    try:
        file_len = len(file_data)
    except TypeError:
        file_len = get_file_size(file_data)
    chunk_count, final_chunk = divmod(file_len, chunk_size)
    if final_chunk:
        chunk_count += 1
    return chunk_generator(chunk_count, chunk_size, file_data)


def max_chunk_count_generator(chunk_count, file_data):
    """
    Generate chunks by defining a maximum number of chunks

    :param chunk_count: Max number of chunks
    :param file_data: bytes data
    :return:
    """
    try:
        # bytes data
        chunk_size = len(file_data) // chunk_count
    except TypeError:
        # file like object
        file_len = get_file_size(file_data)
        chunk_size = file_len // chunk_count

    return chunk_generator(chunk_count, chunk_size, file_data)


def ig_chunk_generator(file_data, max_chunk_size=(500 * 1024)):
    """
    Generate chunks in similar pattern to IG

    :param file_data: bytes data
    :param max_chunk_size:
    :return:
    """
    try:
        total_len = len(file_data)
        is_fp = False
    except TypeError:
        total_len = get_file_size(file_data)
        is_fp = True

    first_chunk_size = 200000
    max_chunk_size = max_chunk_size or (500 * 1024)
    chunks_generated = []
    last_yield_dt = None

    while sum(chunks_generated) < total_len:
        if not chunks_generated or total_len <= first_chunk_size:
            # first chunk
            chunk = Chunk(0, 0, min(first_chunk_size, total_len), 0)
            chunks_generated.append(chunk.length)
        else:
            chunk_elapsed_time = datetime.now() - last_yield_dt
            try:
                new_chunk_size = 5000 * chunks_generated[-1] / int(chunk_elapsed_time.total_seconds() * 1000)
            except ZeroDivisionError:
                new_chunk_size = max_chunk_size
            new_chunk_size = min(max_chunk_size, new_chunk_size)
            chunk_start = sum(chunks_generated)
            chunk_end = min(chunk_start + new_chunk_size, total_len)
            chunk = Chunk(
                len(chunks_generated), sum(chunks_generated), chunk_end,
                0 if chunk_end < total_len else len(chunks_generated) + 1)
            chunks_generated.append(chunk.length)

        last_yield_dt = datetime.now()
        if is_fp:
            file_data.seek(chunk.start, os.SEEK_SET)
            yield chunk, file_data.read(chunk.length)
        else:
            yield chunk, file_data[chunk.start: chunk.end]


def extract_urls(text):
    url_regex = r'((?:(?:http|https|Http|Https|rtsp|Rtsp)://(?:(?:[a-zA-Z0-9$\-\_\.\+\!\*\'\(\)\,\;\?\&\=]|(?:%[a-fA-F0-9]{2})){1,64}(?::(?:[a-zA-Z0-9$\-\_\.\+\!\*\'\(\)\,\;\?\&\=]|(?:%[a-fA-F0-9]{2})){1,25})?@)?)?(?:(?:(?:[a-zA-Z0-9\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF\_][a-zA-Z0-9\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF\_\-]{0,64}\.)+(?:(?:aero|arpa|asia|a[cdefgilmnoqrstuwxz])|(?:biz|b[abdefghijmnorstvwyz])|(?:cat|com|coop|c[acdfghiklmnoruvxyz])|d[ejkmoz]|(?:edu|e[cegrstu])|f[ijkmor]|(?:gov|g[abdefghilmnpqrstuwy])|h[kmnrtu]|(?:info|int|i[delmnoqrst])|(?:jobs|j[emop])|k[eghimnprwyz]|l[abcikrstuvy]|(?:mil|mobi|museum|m[acdeghklmnopqrstuvwxyz])|(?:name|net|n[acefgilopruz])|(?:org|om)|(?:pro|p[aefghklmnrstwy])|qa|r[eosuw]|s[abcdeghijklmnortuvyz]|(?:tel|travel|t[cdfghjklmnoprtvwz])|u[agksyz]|v[aceginu]|w[fs]|(?:\u03B4\u03BF\u03BA\u03B9\u03BC\u03AE|\u0438\u0441\u043F\u044B\u0442\u0430\u043D\u0438\u0435|\u0440\u0444|\u0441\u0440\u0431|\u05D8\u05E2\u05E1\u05D8|\u0622\u0632\u0645\u0627\u06CC\u0634\u06CC|\u0625\u062E\u062A\u0628\u0627\u0631|\u0627\u0644\u0627\u0631\u062F\u0646|\u0627\u0644\u062C\u0632\u0627\u0626\u0631|\u0627\u0644\u0633\u0639\u0648\u062F\u064A\u0629|\u0627\u0644\u0645\u063A\u0631\u0628|\u0627\u0645\u0627\u0631\u0627\u062A|\u0628\u06BE\u0627\u0631\u062A|\u062A\u0648\u0646\u0633|\u0633\u0648\u0631\u064A\u0629|\u0641\u0644\u0633\u0637\u064A\u0646|\u0642\u0637\u0631|\u0645\u0635\u0631|\u092A\u0930\u0940\u0915\u094D\u0937\u093E|\u092D\u093E\u0930\u0924|\u09AD\u09BE\u09B0\u09A4|\u0A2D\u0A3E\u0A30\u0A24|\u0AAD\u0ABE\u0AB0\u0AA4|\u0B87\u0BA8\u0BCD\u0BA4\u0BBF\u0BAF\u0BBE|\u0B87\u0BB2\u0B99\u0BCD\u0B95\u0BC8|\u0B9A\u0BBF\u0B99\u0BCD\u0B95\u0BAA\u0BCD\u0BAA\u0BC2\u0BB0\u0BCD|\u0BAA\u0BB0\u0BBF\u0B9F\u0BCD\u0B9A\u0BC8|\u0C2D\u0C3E\u0C30\u0C24\u0C4D|\u0DBD\u0D82\u0D9A\u0DCF|\u0E44\u0E17\u0E22|\u30C6\u30B9\u30C8|\u4E2D\u56FD|\u4E2D\u570B|\u53F0\u6E7E|\u53F0\u7063|\u65B0\u52A0\u5761|\u6D4B\u8BD5|\u6E2C\u8A66|\u9999\u6E2F|\uD14C\uC2A4\uD2B8|\uD55C\uAD6D|xn--0zwm56d|xn--11b5bs3a9aj6g|xn--3e0b707e|xn--45brj9c|xn--80akhbyknj4f|xn--90a3ac|xn--9t4b11yi5a|xn--clchc0ea0b2g2a9gcd|xn--deba0ad|xn--fiqs8s|xn--fiqz9s|xn--fpcrj9c3d|xn--fzc2c9e2c|xn--g6w251d|xn--gecrj9c|xn--h2brj9c|xn--hgbk6aj7f53bba|xn--hlcj6aya9esc7a|xn--j6w193g|xn--jxalpdlp|xn--kgbechtv|xn--kprw13d|xn--kpry57d|xn--lgbbat1ad8j|xn--mgbaam7a8h|xn--mgbayh7gpa|xn--mgbbh1a71e|xn--mgbc0a9azcg|xn--mgberp4a5d4ar|xn--o3cw4h|xn--ogbpf8fl|xn--p1ai|xn--pgbs0dh|xn--s9brj9c|xn--wgbh1c|xn--wgbl6a|xn--xkc2al3hye2a|xn--xkc2dl3a5ee0h|xn--yfro4i67o|xn--ygbi2ammx|xn--zckzah|xxx)|y[et]|z[amw]))|(?:(?:25[0-5]|2[0-4][0-9]|[0-1][0-9]{2}|[1-9][0-9]|[1-9])\.(?:25[0-5]|2[0-4][0-9]|[0-1][0-9]{2}|[1-9][0-9]|[1-9]|0)\.(?:25[0-5]|2[0-4][0-9]|[0-1][0-9]{2}|[1-9][0-9]|[1-9]|0)\.(?:25[0-5]|2[0-4][0-9]|[0-1][0-9]{2}|[1-9][0-9]|[0-9])))(?::\d{1,5})?(?:/(?:(?:[a-zA-Z0-9\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF\;\/\?\:\@\&\=\#\~\-\.\+\!\*\'\(\)\,\_])|(?:%[a-fA-F0-9]{2}))*)?)(?:\b|$)'
    urls = re.findall(url_regex, text)

    return urls


class InstagramID(object):
    """
    Utility class to convert between IG's internal numeric ID and the shortcode used in weblinks.
    Does NOT apply to private accounts.
    """
    ENCODING_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'

    @staticmethod
    def _encode(num, alphabet=ENCODING_CHARS):
        """Covert a numeric value to a shortcode."""
        if num == 0:
            return alphabet[0]
        arr = []
        base = len(alphabet)
        while num:
            rem = num % base
            num //= base
            arr.append(alphabet[rem])
        arr.reverse()
        return ''.join(arr)

    @staticmethod
    def _decode(shortcode, alphabet=ENCODING_CHARS):
        """Covert a shortcode to a numeric value."""
        base = len(alphabet)
        strlen = len(shortcode)
        num = 0
        idx = 0
        for char in shortcode:
            power = (strlen - (idx + 1))
            num += alphabet.index(char) * (base ** power)
            idx += 1
        return num

    @classmethod
    def weblink_from_media_id(cls, media_id):
        """
        Returns the web link for the media id

        :param media_id:
        :return:
        """
        return 'https://www.instagram.com/p/{0!s}/'.format(cls.shorten_media_id(media_id))

    @classmethod
    def shorten_media_id(cls, media_id):
        """
        Returns the shortcode for a media id

        :param media_id: string in the format id format: AAA_BB where AAA is the pk, BB is user_id
        :return:
        """
        # media id format: AAA_BB where AAA is the pk, BB is user_id
        internal_id = int((str(media_id).split('_')[0]))
        return cls.shorten_id(internal_id)

    @classmethod
    def shorten_id(cls, internal_id):
        """
        Returns the shortcode for a numeric media PK

        :param internal_id: numeric ID value
        :return:
        """
        return cls._encode(internal_id)

    @classmethod
    def expand_code(cls, short_code):
        """
        Returns the numeric ID for a shortcode

        :param short_code:
        :return:
        """
        return cls._decode(short_code)
