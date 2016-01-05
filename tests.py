import os
import shapefile
import shutil
import glob
import sys
import csv

def xcopy(fn_from,fn_to):
    for f in glob.glob(fn_from + '.*'):
        f2 = fn_to + os.path.splitext(f)[1]
        shutil.copy(f,f2)

def cleanup(fn):
    for f in glob.glob(fn + '.*'):
        os.remove(f)
      
def test(i,x):
    if x != correct_values[i]:
        print("Test failed. Expected: %s, got: %s. Continue? [Y/N]" % (correct_values[i],x))
        choice = raw_input().lower()
        if choice not in set(['yes','y', 'ye', '']):
            sys.exit()
            
correct_values = [50,50,50]
os.chdir('tests')
py = 'python ..\extract_values.py -q'

#Test 0
str('Raster(s): 1-band UTM raster. Points: WGS. Output: SHP')
testnum = 0
xcopy('test','test' + str(testnum))
cmd = py + ' -r test%s.shp test_utm.tif' % testnum
os.system(cmd)

sf = shapefile.Reader('test%s.shp' % testnum)
records = sf.records()
x = sum([b for (a,b) in records])
sf = None
cleanup('test%s' % testnum)
test(testnum,x)

#Test 1
str('Raster(s): 1-band WGS raster. Points: WGS. Output: SHP')
testnum = 1
xcopy('test','test' + str(testnum))
cmd = py + ' test%s.shp test_wgs.tif' % testnum
os.system(cmd)

sf = shapefile.Reader('test%s.shp' % testnum)
records = sf.records()
x = sum([b for (a,b) in records])
sf = None
cleanup('test%s' % testnum)
test(testnum,x)

#Test 2
str('Raster(s): 1-band WGS raster. Points: WGS. Output: CSV')
testnum = 2
cmd = py + ' -c test.shp test_wgs.tif'
os.system(cmd)

c = csv.DictReader(open('test_extract.csv','rb'),delimiter=';')
x = sum(float(x['test_wgs']) for x in c)
c = None
os.remove('test_extract.csv')
test(testnum,x)

print('All tests passed sucessfully.')