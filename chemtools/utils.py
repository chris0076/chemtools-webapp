import re
import itertools
import string

from django.template import Template, Context

atom_combinations = (['O', 'S', 'N', 'P', 'C'], ['N', 'P', 'C'])
SCORES = [''.join(x) for x in itertools.product(['E', 'Z'], *atom_combinations)]
DCORES = [''.join(x) for x in itertools.product(['C', 'T'], *atom_combinations)]
CORES = SCORES + DCORES
ARYL0 = ["2","3","8","9"]
ARYL2 = ["4","5","6","7"]
XGROUPS = list(string.uppercase[:12])
RGROUPS = list(string.lowercase[:12])
ARYL = ARYL0 + ARYL2
CLUSTERS = {
    "b": "Blacklight",
    "t": "Trestles",
    "g": "Gordon",
    "c": "Carver",
    "h": "Hooper",
    "m": "Marcy",
}
CLUSTER_TUPLES = [(x, CLUSTERS[x]) for x in CLUSTERS.keys()]

KEYWORDS = "opt B3LYP/6-31g(d)"

COLORS = {
    '1': (255, 255, 255),
    'Ar': (255, 0, 0),
    '2': (0, 255, 0),
    '3': (0, 0, 255),
    'S': (255, 255, 0),
    'O': (255, 0, 0),
    'N': (0, 0, 255),
    'P': (255, 128, 0),
    'Cl': (0, 255, 0),
    'Br': (180, 0, 0),
    'C': (128, 128, 128),
    'H': (220, 220, 220),
    'Si': (128, 170, 128),
}

def catch(fn):
    '''Decorator to catch all exceptions and log them.'''
    def wrapper(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except Exception as e:
            self.errors.append(repr(e))
    return wrapper


class Output(object):
    def __init__(self):
        self.errors = []
        self.output = []

    def write(self, line, newline=True):
        try:
            if newline:
                self.output.append(line)
            else:
                self.output[-1] += line
        except IndexError:
            self.output.append(line)

    def format_output(self, errors=True):
        a = self.output[:]
        if errors:
            a += ["\n---- Errors (%i) ----" % len(self.errors)] + self.errors
        return '\n'.join(a) + "\n"

    @catch
    def parse_file(self, f):
        raise NotImplementedError


def write_job(**kwargs):
    if "cluster" in kwargs and kwargs["cluster"] in CLUSTERS.keys():
        template = Template(kwargs.get("template", ''))
        c = Context({
            "name": kwargs["name"],
            "email": kwargs["email"],
            "nodes": kwargs["nodes"],
            "ncpus": int(kwargs["nodes"]) * 16,
            "time": "%s:00:00" % kwargs["walltime"],
            "internal": kwargs.get("internal", ''),
            "allocation": kwargs["allocation"],
            })

        return template.render(c)
    else:
        return ''

def name_expansion(string):
    braceparse = re.compile(r"""(\{[^\{\}]*\})""")
    varparse = re.compile(r"\$\w*")

    variables = {
        "SCORES":   ','.join(SCORES),
        "DCORES":   ','.join(DCORES),
        "CORES":    ','.join(CORES),
        "RGROUPS":  ','.join(RGROUPS),
        "XGROUPS":  ','.join(XGROUPS),
        "ARYL":     ','.join(ARYL),
        "ARYL0":    ','.join(ARYL0),
        "ARYL2":    ','.join(ARYL2),
    }

    def get_var(name):
        try:
            newname = name.group(0).lstrip("$")
        except AttributeError:
            newname = name.lstrip("$")

        try:
            x = variables[newname]
        except:
            try:
                int(newname)
                x = "*" + newname
            except:
                x = newname
        return x

    def split_molecules(string):
        count = 0
        parts = ['']
        for i, char in enumerate(string):
            if char == "," and not count:
                parts.append('')
            else:
                if char == "{":
                    count += 1
                elif char == "}":
                    count -= 1
                parts[-1] += char
        assert not count
        return parts

    def expand(items):
        swapped = [re.sub(varparse, get_var, x) for x in items]
        a = [x[1:-1].split(',') for x in swapped[1::2] if x[1] != "*"]
        operations = {
            "":  lambda x: x,
            "L": lambda x: x.lower(),
            "U": lambda x: x.upper()
        }

        out = []
        for stuff in itertools.product(*a):
            temp = []
            i = 0
            for thing in swapped[1::2]:
                if thing[1] == "*":
                    split = thing.strip("{*}").split(".")
                    num = split[0]
                    if len(split) > 1:
                        op = operations[split[1].upper()]
                    else:
                        op = operations['']
                    x = op(stuff[int(num)])
                else:
                    x = stuff[i]
                    i += 1
                temp.append(x)
            out.append(temp)

        return [''.join(sum(zip(swapped[::2], x), ()) + (swapped[-1], )) for x in out]

    braces = []
    inter = set('{}').intersection
    for part in split_molecules(string):
        if inter(part):
            braces.extend(expand(re.split(braceparse, part)))
        else:
            braces.append(part)
    return braces