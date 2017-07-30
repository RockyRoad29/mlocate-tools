# coding=utf-8
import logging
logging.basicConfig(level=10)

class Tree:
    """
    >>> o = Tree("/run/media/MyBook/"); o.rel_path
    ''
    >>> o.load("/run/media/MyBook/Archives")
    'Archives/'
    >>> o.load("/run/media/MyBook/Archives/2012")
    'Archives/2012/'
    >>> o.load("/run/media/MyBook/Archives/2017/02")
    'Archives/2017/02/'
    >>> o.depth
    3
    >>> o.load("/run/media/MyBook/Backup/2017-02")
    'Backup/2017-02/'
    >>> o.load("/run/media/Elsewhere") is None
    True
    >>> o.tree
    [['Archives', [['2012', []], ['2017', [['02', []]]]]], ['Backup', [['2017-02', []]]]]
    >>> o.as_string()
    - Archives
      - 2012
      - 2017
        - 02
    - Backup
      - 2017-02
    >>> o.print_graph()
    ├── Archives
    │   ├── 2012
    │   └── 2017
    │       └── 02
    └── Backup
        └── 2017-02
    """
    def __init__(self, root=""):
        logging.info("Creating tree from %r", root)
        self.root = root
        self.rel_path = ""
        self.stack = []
        self.tree = []
        #self.tip = self.tree

    @property
    def depth(self):
        return len(self.stack)

    def load(self, node_path):

        if not node_path.startswith(self.root):
            return None

        p1 = len(self.root)
        current = node_path[p1:]
        nodes = self.split(current)

        p2 = 0
        for p in range(min(len(nodes), len(self.stack))):
            if nodes[p] != self.stack[p]:
                break
            p2 = p+1

        while (p2 < self.depth):
            self.pop()

        self.pushx(nodes[p2:])
        self.rel_path = current + '/'
        return self.rel_path

    def push(self, node):
        logging.info("push(%r)", node)

        tip = self.tree
        for i in range(self.depth): tip = tip[-1][1]
        # can't easily go back when popping, so compute each time
        tip.append([node, []])

        self.stack.append(node)

    def pop(self):
        node = self.stack.pop()
        logging.info("pop() => %r", node)
        return node

    def pushx(self, nodes):
        logging.info("pushx(%r) onto %r", nodes, self.stack)
        if not nodes:
            return
        if len(nodes) != 1:
            logging.warning("pushing %d nodes at once", len(nodes))
        for node in nodes:
            self.push(node)

    def split(self, rel_path):
        return rel_path.split('/')

    def as_string(self):
        indent='  '
        bullet = '- '
        def _level(d, st):
            prefix = indent * d + bullet
            for subtree in st:
                print(prefix + subtree[0])
                _level(d+1, subtree[1])

        _level(0, self.tree)

    def print_graph(self, max_depth=0):
        def _level(prefix, depth,  st):
            if st == []: return
            if max_depth and depth >= max_depth:
                logging.info("Maximum depth reached, omitting details")
                return

            #pfx = prefix + '├── '
            for subtree in st[:-1]:
                print(prefix + '├── '  + subtree[0])
                _level(prefix + "│   ", depth + 1, subtree[1])

            print(prefix + '└── ' + st[-1][0])
            _level(prefix + '    ' , depth + 1, st[-1][1])

        _level('', 0, self.tree)

    def as_graph0(self):
        indents = ('├── ', '└── ')
        def _level(pfx, st):
            if st == []: return
            prefix = pfx + indents[0]
            for subtree in st[:-1]:
                print(prefix + subtree[0])
                _level(prefix, subtree[1])

            prefix = pfx + indents[1]
            print(prefix + st[-1][0])
            _level(prefix , st[-1][1])

        _level('', self.tree)
