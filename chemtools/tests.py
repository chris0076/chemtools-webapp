from itertools import product, permutations

from django.test import TestCase

import gjfwriter
import utils
import constants
import extractor
import mol_name


class GJFWriterTestCase(TestCase):
    templates = [
        "{0}_TON",
        "CON_{0}",
        "TON_{0}_",
        "{0}_TPN_{0}",
        "{0}_TNN_{0}_",
        "CPP_{0}_{0}",
        "{0}_TON_{0}_{0}",
    ]
    cores = constants.CORES
    invalid_cores = ["cao", "bo", "CONA", "asD"]
    valid_polymer_sides = ['2', '4b', '4bc', '44bc', '5-', '5-5', '55-', '5-a', '5-ab4-']
    invalid_polymer_sides = ['B', '2B']
    valid_sides = valid_polymer_sides + invalid_polymer_sides
    invalid_sides = ['~', 'b', 'c', 'BB', 'TON', 'Dc', '4aaa', '24C2', 'awr', 'A-', '5B-']
    valid_polymer_options = ['_n1', '_n2', '_n3', '_m1', '_m2', '_m3', '_n1_m1']
    invalid_polymer_options = ['_n2_m2', '_n3_m3', '_m2_n2', '_m3_n3', '_n0', '_m0', '_n0_m0']

    def setUp(self):
        pass

    def test_cores(self):
        for core in self.cores:
            gjfwriter.GJFWriter(core)

    def test_invalid_cores(self):
        for core in self.invalid_cores:
            try:
                gjfwriter.GJFWriter(core)
                raise ValueError
            except:
                pass

    def test_sides(self):
        errors = []
        sets = [
            self.templates,
            self.valid_sides,
        ]
        for template, group in product(*sets):
            name = template.format(group)
            try:
                gjfwriter.GJFWriter(name)
            except Exception as e:
                errors.append((name, e))
        if errors:
            print errors
            raise errors[0][1]

    def test_invalid_sides(self):
        errors = []
        sets = [
            self.templates,
            self.invalid_sides,
        ]
        for template, group in product(*sets):
            name = template.format(group)
            try:
                gjfwriter.GJFWriter(name)
                if group != "TON" and name != "CON_BB":
                    errors.append(name)
            except Exception:
                pass
        if errors:
            print errors
            raise ValueError

    def test_polymer(self):
        errors = []
        sets = [
            self.templates,
            self.valid_polymer_sides,
            self.valid_polymer_options
        ]
        for template, group, option in product(*sets):
            name = template.format(group) + option
            try:
                gjfwriter.GJFWriter(name)
            except Exception as e:
                errors.append((name, e))
        if errors:
            print errors
            raise errors[0][1]

    def test_invalid_polymer(self):
        errors = []
        sets = [
            self.templates,
            self.valid_sides,
            self.invalid_polymer_options
        ]
        for template, group, option in product(*sets):
            name = template.format(group) + option
            try:
                gjfwriter.GJFWriter(name)
                errors.append(name)
            except Exception:
                pass
        if errors:
            print errors
            raise ValueError

    def test_single_axis_expand(self):
        errors = []
        sets = [
            self.valid_sides,
            ['x', 'y', 'z'],
            ['1', '2', '3']
        ]
        for group, axis, num  in product(*sets):
            name = self.templates[0].format(group) + '_' + axis + num
            try:
                gjfwriter.GJFWriter(name)
            except Exception as e:
                errors.append((name, e))
        if errors:
            print errors
            raise errors[0][1]

    def test_multi_axis_expand(self):
        errors = []
        sets = [
            self.valid_sides,
            ['_x1', '_x2', '_x3'],
            ['_y1', '_y2', '_y3'],
            ['_z1', '_z2', '_z3'],
        ]
        for group, x, y, z in product(*sets):
            name = self.templates[0].format(group) + x + z + z
            try:
                gjfwriter.GJFWriter(name)
            except Exception as e:
                errors.append((name, e))
        if errors:
            raise errors[0][1]

    def test_manual_polymer(self):
        errors = []
        sets = [
            self.templates[1:-1],
            self.valid_polymer_sides,
            [2, 3, 4],
        ]
        for template, group, num in product(*sets):
            name = '_'.join([template.format(group)] * num)
            try:
                gjfwriter.GJFWriter(name)
            except Exception as e:
                errors.append((name, e))
        if errors:
            print errors
            raise errors[0][1]

    def test_invalid_manual_polymer(self):
        errors = []
        sets = [
            self.templates,
            self.invalid_polymer_sides,
            [2, 3, 4],
        ]
        for template, group, num in product(*sets):
            name = '_'.join([template.format(group)] * num)
            try:
                gjfwriter.GJFWriter(name)
                if "__" in name:
                    continue
                if any(x.endswith("B") for x in name.split("_TON_")):
                    continue
                errors.append(name)
            except Exception:
                pass
        if errors:
            print errors
            raise ValueError

    def test_spot_check(self):
        errors = []
        names = [
            '5ba_TON_5ba55_TON_345495_2_TON_n6',
            '24a_TON_35b_24c',
            '24a_TON_B24a',
            'TON_24a_24a',
            '24a_TON_24a',
            '24a_TON',
            '4a_TON_n2',
            '4a_TON_B24c_n3',
            '4a_TON_35_2_m3',
            'TON_24a_24a_TON',
            'TON_24a__TON',
            'TON__24a_TON',
            '4a_TON_5555555555_4a',
            '5_TON_n13',
        ]
        for name in names:
            try:
                gjfwriter.GJFWriter(name)
            except Exception as e:
                errors.append((name, e))
        if errors:
            print errors
            raise errors[0][1]

    def test_png(self):
        errors = []
        sets = [
            self.templates,
            self.valid_sides,
        ]
        for template, group in product(*sets):
            name = template.format(group)
            try:
                obj = gjfwriter.GJFWriter(name)
                obj.get_png()
            except Exception as e:
                errors.append((name, e))
        if errors:
            print errors
            raise errors[0][1]

    def test_gjf(self):
        errors = []
        sets = [
            self.templates,
            self.valid_sides,
        ]
        for template, group in product(*sets):
            name = template.format(group)
            try:
                obj = gjfwriter.GJFWriter(name)
                obj.get_gjf()
            except Exception as e:
                errors.append((name, e))
        if errors:
            print errors
            raise errors[0][1]

    def test_mol2(self):
        errors = []
        sets = [
            self.templates,
            self.valid_sides,
        ]
        for template, group in product(*sets):
            name = template.format(group)
            try:
                obj = gjfwriter.GJFWriter(name)
                obj.get_mol2()
            except Exception as e:
                errors.append((name, e))
        if errors:
            print errors
            raise errors[0][1]


class MolNameTestCase(TestCase):
    pairs = [
        ('TON', 'A**_TON_A**_A**'),

        ('2_TON', '2**A**_TON_A**_A**'),
        ('2-_TON', '2**-A**_TON_A**_A**'),
        ('4_TON', '4aaA**_TON_A**_A**'),
        ('4b_TON', '4bbA**_TON_A**_A**'),
        ('4bc_TON', '4bcA**_TON_A**_A**'),
        ('44bc_TON', '4aa4bcA**_TON_A**_A**'),

        ('TON_2', 'A**_TON_A**_2**A**'),
        ('TON_4', 'A**_TON_A**_4aaA**'),
        ('TON_4b', 'A**_TON_A**_4bbA**'),
        ('TON_4bc', 'A**_TON_A**_4bcA**'),
        ('TON_44bc', 'A**_TON_A**_4aa4bcA**'),

        ('TON_2_', 'A**_TON_2**A**_A**'),
        ('TON_4_', 'A**_TON_4aaA**_A**'),
        ('TON_4b_', 'A**_TON_4bbA**_A**'),
        ('TON_4bc_', 'A**_TON_4bcA**_A**'),
        ('TON_44bc_', 'A**_TON_4aa4bcA**_A**'),

        ('TON_2_TON_2', 'A**_TON_A**_2**_TON_A**_2**A**'),
        ('TON_4_TON_4', 'A**_TON_A**_4aa_TON_A**_4aaA**'),
        ('TON_4b_TON_4b', 'A**_TON_A**_4bb_TON_A**_4bbA**'),
        ('TON_4bc_TON_4bc', 'A**_TON_A**_4bc_TON_A**_4bcA**'),
        ('TON_44bc_TON_44bc', 'A**_TON_A**_4aa4bc_TON_A**_4aa4bcA**'),

        ('TON_2_TON_2_TON_2', 'A**_TON_A**_2**_TON_A**_2**_TON_A**_2**A**'),
        ('TON_4_TON_4_TON_4', 'A**_TON_A**_4aa_TON_A**_4aa_TON_A**_4aaA**'),
        ('TON_4b_TON_4b_TON_4b', 'A**_TON_A**_4bb_TON_A**_4bb_TON_A**_4bbA**'),
        ('TON_4bc_TON_4bc_TON_4bc', 'A**_TON_A**_4bc_TON_A**_4bc_TON_A**_4bcA**'),
        ('TON_44bc_TON_44bc_TON_44bc', 'A**_TON_A**_4aa4bc_TON_A**_4aa4bc_TON_A**_4aa4bcA**'),

        ('TON_2__TON_2_', 'A**_TON_2**A**__TON_2**A**_A**'),
        ('TON_4__TON_4_', 'A**_TON_4aaA**__TON_4aaA**_A**'),
        ('TON_4b__TON_4b_', 'A**_TON_4bbA**__TON_4bbA**_A**'),
        ('TON_4bc__TON_4bc_', 'A**_TON_4bcA**__TON_4bcA**_A**'),
        ('TON_44bc__TON_44bc_', 'A**_TON_4aa4bcA**__TON_4aa4bcA**_A**'),
    ]
    polymer_pairs = [
            ('TON_n2', '_TON_A**__n2_m1'),

            ('2_TON_n2', '2**_TON_A**__n2_m1'),
            ('4_TON_n2', '4aa_TON_A**__n2_m1'),
            ('4b_TON_n2', '4bb_TON_A**__n2_m1'),
            ('4bc_TON_n2', '4bc_TON_A**__n2_m1'),
            ('44bc_TON_n2', '4aa4bc_TON_A**__n2_m1'),

            ('TON_2_n2', '_TON_A**_2**_n2_m1'),
            ('TON_4_n2', '_TON_A**_4aa_n2_m1'),
            ('TON_4b_n2', '_TON_A**_4bb_n2_m1'),
            ('TON_4bc_n2', '_TON_A**_4bc_n2_m1'),
            ('TON_44bc_n2', '_TON_A**_4aa4bc_n2_m1'),
            ('TON_B4bc_n2', '_TON_B**_4bc_n2_m1'),  # special case

            ('TON_2__n2', '_TON_2**A**__n2_m1'),
            ('TON_4__n2', '_TON_4aaA**__n2_m1'),
            ('TON_4b__n2', '_TON_4bbA**__n2_m1'),
            ('TON_4bc__n2', '_TON_4bcA**__n2_m1'),
            ('TON_44bc__n2', '_TON_4aa4bcA**__n2_m1'),

            ('TON_2_TON_2_n2', '_TON_A**_2**_TON_A**_2**_n2_m1'),
            ('TON_4_TON_4_n2', '_TON_A**_4aa_TON_A**_4aa_n2_m1'),
            ('TON_4b_TON_4b_n2', '_TON_A**_4bb_TON_A**_4bb_n2_m1'),
            ('TON_4bc_TON_4bc_n2', '_TON_A**_4bc_TON_A**_4bc_n2_m1'),
            ('TON_44bc_TON_44bc_n2', '_TON_A**_4aa4bc_TON_A**_4aa4bc_n2_m1'),

            ('TON_2_TON_2_TON_2_n2', '_TON_A**_2**_TON_A**_2**_TON_A**_2**_n2_m1'),
            ('TON_4_TON_4_TON_4_n2', '_TON_A**_4aa_TON_A**_4aa_TON_A**_4aa_n2_m1'),
            ('TON_4b_TON_4b_TON_4b_n2', '_TON_A**_4bb_TON_A**_4bb_TON_A**_4bb_n2_m1'),
            ('TON_4bc_TON_4bc_TON_4bc_n2', '_TON_A**_4bc_TON_A**_4bc_TON_A**_4bc_n2_m1'),
            ('TON_44bc_TON_44bc_TON_44bc_n2', '_TON_A**_4aa4bc_TON_A**_4aa4bc_TON_A**_4aa4bc_n2_m1'),

            ('TON_2__TON_2__n2', '_TON_2**A**__TON_2**A**__n2_m1'),
            ('TON_4__TON_4__n2', '_TON_4aaA**__TON_4aaA**__n2_m1'),
            ('TON_4b__TON_4b__n2', '_TON_4bbA**__TON_4bbA**__n2_m1'),
            ('TON_4bc__TON_4bc__n2', '_TON_4bcA**__TON_4bcA**__n2_m1'),
            ('TON_44bc__TON_44bc__n2', '_TON_4aa4bcA**__TON_4aa4bcA**__n2_m1'),

            ('TON_m2', 'A**_TON__A**_n1_m2'),

            ('2_TON_m2', '2**A**_TON__A**_n1_m2'),
            ('4_TON_m2', '4aaA**_TON__A**_n1_m2'),
            ('4b_TON_m2', '4bbA**_TON__A**_n1_m2'),
            ('4bc_TON_m2', '4bcA**_TON__A**_n1_m2'),
            ('44bc_TON_m2', '4aa4bcA**_TON__A**_n1_m2'),

            ('TON_2_m2', 'A**_TON__2**A**_n1_m2'),
            ('TON_4_m2', 'A**_TON__4aaA**_n1_m2'),
            ('TON_4b_m2', 'A**_TON__4bbA**_n1_m2'),
            ('TON_4bc_m2', 'A**_TON__4bcA**_n1_m2'),
            ('TON_44bc_m2', 'A**_TON__4aa4bcA**_n1_m2'),

            ('TON_2__m2', 'A**_TON_2**_A**_n1_m2'),
            ('TON_4__m2', 'A**_TON_4aa_A**_n1_m2'),
            ('TON_4b__m2', 'A**_TON_4bb_A**_n1_m2'),
            ('TON_4bc__m2', 'A**_TON_4bc_A**_n1_m2'),
            ('TON_44bc__m2', 'A**_TON_4aa4bc_A**_n1_m2'),
        ]

    def test_brace_expansion(self):
        names = [
            ("a", ["a"]),
            ("{a,b}", ["a", "b"]),
            ("{a,b}c", ["ac", "bc"]),
            ("c{a,b}", ["ca", "cb"]),
            ("{a,b}{c}", ["ac", "bc"]),
            ("{c}{a,b}", ["ca", "cb"]),
            ("{a,b}{c,d}", ["ac", "bc", "ad", "bd"]),
            ("e{a,b}{c,d}", ["eac", "ebc", "ead", "ebd"]),
            ("{a,b}e{c,d}", ["aec", "bec", "aed", "bed"]),
            ("{a,b}{c,d}e", ["ace", "bce", "ade", "bde"]),
            ("{a,b}{c,d}{e,f}", ["ace", "acf", "ade", "adf", "bce", "bcf", "bde", "bdf"]),
        ]
        for name, result in names:
            self.assertEqual(set(mol_name.name_expansion(name)), set(result))

    def test_group_expansion(self):
        names = [
            ("{$CORES}", constants.CORES),
            ("{$XGROUPS}", constants.XGROUPS),
            ("{$RGROUPS}", constants.RGROUPS),
            ("{$ARYL0}", constants.ARYL0),
            ("{$ARYL2}", constants.ARYL2),
            ("{$ARYL}", constants.ARYL),
        ]
        for name, result in names:
            self.assertEqual(set(mol_name.name_expansion(name)), set(result))

    def test_local_vars(self):
        names = [
            ("{a,b}{$0}", ["aa", "bb"]),
            ("{a,b}{$0}{$0}", ["aaa", "bbb"]),
            ("{a,b}{c,d}{$0}{$0}", ["acaa", "bcbb", "adaa", "bdbb"]),
            ("{a,b}{c,d}{$1}{$1}", ["accc", "bccc", "addd", "bddd"]),
            ("{a,b}{c,d}{$0}{$1}", ["acac", "bcbc", "adad", "bdbd"]),
        ]
        for name, result in names:
            self.assertEqual(set(mol_name.name_expansion(name)), set(result))

    def test_name_expansion(self):
        names = [
            ("24{$RGROUPS}_{$CORES}", ["24" + '_'.join(x) for x in product(constants.RGROUPS, constants.CORES)]),
            ("24{$XGROUPS}_{$CORES}", ["24" + '_'.join(x) for x in product(constants.XGROUPS, constants.CORES)]),
            ("24{$ARYL}_{$CORES}", ["24" + '_'.join(x) for x in product(constants.ARYL, constants.CORES)]),
        ]
        for name, result in names:
            self.assertEqual(set(mol_name.name_expansion(name)), set(result))

    def test_local_vars_case(self):
        names = [
            ("{a,b}{$0.U}", ["aA", "bB"]),
            ("{a,b}{$0.U}{$0}", ["aAa", "bBb"]),
            ("{a,b}{c,d}{$0.U}{$0.U}", ["acAA", "bcBB", "adAA", "bdBB"]),
            ("{a,b}{c,d}{$1}{$1.U}", ["accC", "bccC", "addD", "bddD"]),
            ("{a,b}{c,d}{$0.U}{$1.U}", ["acAC", "bcBC", "adAD", "bdBD"]),
            ("{A,B}{$0.L}", ["Aa", "Bb"]),
            ("{A,B}{$0.L}{$0}", ["AaA", "BbB"]),
            ("{A,B}{C,D}{$0.L}{$0.L}", ["ACaa", "BCbb", "ADaa", "BDbb"]),
            ("{A,B}{C,D}{$1}{$1.L}", ["ACCc", "BCCc", "ADDd", "BDDd"]),
            ("{A,B}{C,D}{$0.L}{$1.L}", ["ACac", "BCbc", "ADad", "BDbd"]),
        ]
        for name, result in names:
            self.assertEqual(set(mol_name.name_expansion(name)), set(result))

    def test_get_exact_name(self):
        errors = []
        for name, expected in self.pairs:
            try:
                a = mol_name.get_exact_name(name)
                expected = expected + "_n1_m1_x1_y1_z1"
                assert a == expected.replace('*','')
            except Exception as e:
                print e
                errors.append((a, expected, e))
        if errors:
            print errors
            raise errors[0][1]

    def test_get_exact_name_polymer(self):
        errors = []
        for name, expected in self.polymer_pairs:
            try:
                a = mol_name.get_exact_name(name)
                expected = expected + "_x1_y1_z1"
                assert a == expected.replace('*', '')
            except Exception as e:
                print e
                errors.append((a, expected, e))
        if errors:
            print errors
            raise errors[0][2]

    def test_get_exact_name_spacers(self):
        errors = []
        for name, expected in self.pairs:
            try:
                a = mol_name.get_exact_name(name, spacers=True)
                expected = expected + "_n1_m1_x1_y1_z1"
                assert a == expected
            except Exception as e:
                print e
                errors.append((a, expected, e))
        if errors:
            print errors
            raise errors[0][1]

    def test_get_exact_name_polymer_spacers(self):
        errors = []
        for name, expected in self.polymer_pairs:
            try:
                a = mol_name.get_exact_name(name, spacers=True)
                expected = expected + "_x1_y1_z1"
                assert a == expected
            except Exception as e:
                print e
                errors.append((a, expected, e))
        if errors:
            print errors
            raise errors[0][2]


# class ExtractorTestCase(TestCase):
#     def test_run_all(self):
#         extractor.run_all()
