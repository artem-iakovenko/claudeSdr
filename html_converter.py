import html2text


def convert_to_text(html_content):
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.ignore_images = True
    converter.body_width = 0
    plain_text = converter.handle(html_content)
    return plain_text.strip()
