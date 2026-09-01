from argparse     import ArgumentParser
from html.parser  import HTMLParser
from pathlib      import Path
from re           import sub
from urllib.parse import urljoin, urlsplit


class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonical = ''
        self.link      = ''
        self.markdown  = []

        self.in_article     = False
        self.ignore_depth   = 0
        self.ignore_classes = {'permalink', 'anchor'}
        self.ignore_tags    = {'nav', 'button', 'script', 'style', 'aside', 'header', 'footer', 'svg', 'form'}

        self.in_admonition   = 0
        self.admonition_type = ''

        self.in_pre = False

        self.in_table       = 0
        self.num_of_columns = 0
        self.is_header_row  = False


    def is_doc_link(self, base, link):
        url = urlsplit(urljoin(base, link))

        valid_domain = url.netloc == "documentation.suse.com"
        valid_path   = url.path.endswith(".html") or url.path.endswith("/")

        return valid_domain and valid_path


    def is_canonical(self, attrs):
        if attrs.get('rel', '') == 'canonical':
            self.canonical = attrs.get('href', '')
            return True
        return False


    def should_ignore(self, tag, classes):
        if self.ignore_depth > 0 or tag in self.ignore_tags or (classes & self.ignore_classes):
            self.ignore_depth += 1
            return True
        return False


    def is_admonition(self, classes):
        if 'admonitionblock' in classes:
            if 'note' in classes:
                self.markdown.append('> :pencil: **Note**')
            elif 'important' in classes:
                self.markdown.append('> :warning: **Important**')
            return True
        return False


    def handle_starttag(self, tag, attrs):
        if tag == 'article':
            self.in_article = True
            return

        if not self.in_article and tag != 'link':
            return

        attrs   = dict(attrs)
        classes = set(attrs.get('class', '').split())

        if tag == 'link':
            self.is_canonical(attrs)
            return

        if self.should_ignore(tag, classes):
            return

        # if self.is_admonition(classes):
        #     return

        # breakpoint()
        match tag:
            case 'div':
                if self.is_admonition(classes):
                    self.in_admonition += 1
            case 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6':
                self.markdown.append('\n' + '#' * int(tag[1]) + ' ')
            case 'p' | 'dt':
                self.markdown.append('')
            case 'li':
                self.markdown.append('* ')
            case 'strong' | 'b':
                self.markdown.append('**')
            case 'em' | 'i' if 'caret' in classes:
                self.markdown.append(' > ')
                self.ignore_depth += 1
            case 'em' | 'i':
                self.markdown.append('*')
            case 'pre':
                self.in_pre = True
                self.markdown.append('\n\n```\n')
            case 'code':
                if not self.in_pre:
                    self.markdown.append('`')
            case 'caption':
                self.markdown.append('\n**')
            case 'table':
                self.markdown.append('\n')
                self.in_table += 1
            case 'tr':
                if self.in_admonition > 0:
                    self.markdown.append('> ')
                else:
                    self.markdown.append('|')
                    self.is_header_row = False
                    self.num_of_columns = 0
            case 'th':
                self.is_header_row = True
            case 'a':
                self.link = attrs.get('href', '')
                if self.link:
                    self.markdown.append('[')
                    if self.is_doc_link(self.canonical, self.link):
                        self.link = self.link.replace('.html', '.md', 1)


    def handle_endtag(self, tag):
        if not self.in_article:
            return

        # breakpoint()
        if self.ignore_depth > 0:
            self.ignore_depth -= 1
            return

        match tag:
            case 'div' if self.in_admonition > 0:
                self.in_admonition -= 1
                if not self.in_admonition:
                    self.markdown.append('\n')
            case 'article':
                self.in_article = False
            case 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6':
                self.markdown.append('\n')
            case 'p':
                if not self.in_table:
                    self.markdown.append('\n')
            case 'strong' | 'b':
                self.markdown.append('** ')
            case 'em' | 'i':
                self.markdown.append('* ')
            case 'pre':
                self.in_pre = False
                self.markdown.append('\n```\n\n')
            case 'code':
                if not self.in_pre:
                    self.markdown.append('` ')
            case 'caption':
                self.markdown.append('**\n')
            case 'th' | 'td':
                if not self.in_admonition:
                    self.markdown.append('|')
                    self.num_of_columns += 1
            case 'tr':
                self.markdown.append('\n')
                # If this was the table header row, add the Markdown divider (---|---)
                if self.is_header_row:
                    self.markdown.append('|' + ' --- |' * self.num_of_columns + '\n')
            case 'table':
                self.in_table -= 1
            case 'a':
                if self.link:
                    self.markdown.append(f']({self.link})')
                    self.link = ''


    def handle_data(self, data):
        if self.in_article and self.ignore_depth == 0:
            # breakpoint()
            if self.in_pre:
                # Preserve exact formatting inside code blocks
                self.markdown.append(data)
            else:
                # Condense whitespace for standard text (prevents weird line breaks)
                text = sub(r'\s+', ' ', data)
                text = text.lstrip()
                if text:
                    self.markdown.append(text)


    def get_result(self):
        raw_text = "".join(self.markdown)
        #clean_text = sub(r'\n{3,}', '\n\n', raw_text)
        clean_text = sub(r'\n ', '\n', raw_text)
        return clean_text


if __name__ == "__main__":
    argumentparser = ArgumentParser(
        description="Convert a HTML file into clean Markdown for LLMs."
    )
    argumentparser.add_argument(
        "filepath",
        type=str,
        help="Path to the HTML file."
    )
    args = argumentparser.parse_args()

    file = Path(args.filepath)
    if not file.exists():
        raise FileNotFoundError(f"File '{file}' does not exist.")

    try:
        html = file.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error processing {file}: {e}")

    parser = ArticleParser()
    parser.feed(html)
    print(parser.get_result())
