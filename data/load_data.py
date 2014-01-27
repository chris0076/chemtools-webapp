import csv

from chemtools.mol_name import get_exact_name
from models import DataPoint


with open("data/data.csv", "r") as csvfile:
    reader = csv.reader(csvfile, delimiter=',', quotechar='"')
    points = []
    for row in reader:
        if row == []:
            continue
        try:
            band_gap = row[10]
            if band_gap == '---':
                band_gap = None
            options = row[4]

            try:
                exact_name = get_exact_name(row[1])
            except:
                exact_name = None

            print row[1]
            point = DataPoint(
                    name=row[1], options=row[4],
                    occupied=row[5], virtual=row[6],
                    homo_orbital=row[7], dipole=row[8],
                    energy=row[9], band_gap=band_gap,
                    exact_name=exact_name)
            point.clean_fields()
            points.append(point)
        except Exception as e:
            print e
    DataPoint.objects.bulk_create(points)
