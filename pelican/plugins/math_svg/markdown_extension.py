import hashlib
from pathlib import Path
import re
import shelve
import subprocess
import sys
from typing import Any, List, Optional
from xml.etree.ElementTree import Element

if (sys.version_info[0] >= 3) and (sys.version_info[1] >= 7):
    Match = re.Match
else:
    Match = Any

import markdown


def render_svg(math: str) -> str:
    checksum = hashlib.md5(math.encode()).hexdigest()
    path_shelf = Path(".cache") / "pelican-math-svg"
    path_shelf.parent.mkdir(exist_ok=True, parents=True)

    with shelve.open(str(path_shelf)) as shelf:
        if checksum in shelf:
            result = shelf[checksum]
        else:
            result = (
                subprocess.check_output(["tex2svg", "--ex", "10", "{}" + math])
                .decode()
                .strip()
            )
            shelf[checksum] = result

    return result


class PelicanMathPattern(markdown.inlinepatterns.Pattern):
    def __init__(self, extension, tag: str, pattern: str):
        super().__init__(pattern)

        self.math_class = "math"
        self.pelican_math_extension = extension
        self.tag = tag

    def handleMatch(self, m: Match) -> Element:
        node = Element(self.tag)
        node.set("class", self.math_class)

        # prefix = "\\(" if m.group("prefix") == "$" else m.group("prefix")
        # suffix = "\\)" if m.group("suffix") == "$" else m.group("suffix")
        # node.text = markdown.util.AtomicString(prefix + m.group("math") + suffix)
        node.text = render_svg(m.group("math"))
        return node


class PelicanMathFixDisplay(markdown.treeprocessors.Treeprocessor):
    def __init__(self, extension):
        self.math_class = "math"
        self.pelican_math_extension = extension

    def fix_display_math(
        self,
        root: Element,
        children: List[Element],
        math_divs: List[int],
        insert_index: int,
        text: Optional[str],
    ):
        current_index = 0
        for index in math_divs:
            element = Element("p")
            element.text = text
            element.extend(children[current_index:index])

            if (len(element) != 0) or (element.text and not element.text.isspace()):
                root.insert(insert_index, element)
                insert_index += 1

            text = children[index].tail
            children[index].tail = None
            root.insert(insert_index, children[index])
            current_index = index + 1

        element = Element("p")
        element.text = text
        element.extend(children[current_index:])

        if (len(element) != 0) or (element.text and not element.text.isspace()):
            root.insert(insert_index, element)

    def run(self, root: Element) -> Element:
        for parent in root:
            math_divs = []
            children = list(parent)

            for div in parent.findall("div"):
                if div.get("class") == self.math_class:
                    math_divs.append(children.index(div))

            if not math_divs:
                continue

            insert_idx = list(root).index(parent)
            self.fix_display_math(root, children, math_divs, insert_idx, parent.text)
            root.remove(parent)

        return root
