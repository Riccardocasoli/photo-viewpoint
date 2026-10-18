import unittest
from .layout_arrange import arrange, fit_size, caption_text


class ArrangeTests(unittest.TestCase):
    page=(0,0,297,210)
    def records(self,n):
        return [{'fid':i,'anchor':(70+i*7,30+i*9),'size':(38,19)} for i in range(n)]

    def test_landscape_portrait_square_fit(self):
        self.assertEqual(fit_size(4000,2000,40,30),(40,20))
        self.assertEqual(fit_size(2000,4000,40,30),(15,30))
        self.assertEqual(fit_size(2000,2000,40,30),(30,30))

    def test_arbitrary_sizes_preserve_ratio(self):
        for pw,ph in [(4032,3024),(3024,4032),(10000,300),(100,100)]:
            for mw,mh in [(38,26),(100,80),(12.345,67.89)]:
                w,h=fit_size(pw,ph,mw,mh)
                self.assertLessEqual(w,mw+1e-8)
                self.assertLessEqual(h,mh+1e-8)
                self.assertAlmostEqual(w/h,pw/ph)

    def test_map_and_other_extents_are_irrelevant(self):
        records=self.records(3)
        a=arrange(records,self.page,(0,0,297,210))
        b=arrange(records,self.page,(-10000,-10000,10000,10000))
        self.assertEqual(a,b)
        self.assertEqual(len(a),3)
        self.assertEqual(a[0]['box'][2:],(38,19))

    def test_second_page_coordinates(self):
        result=arrange(self.records(1),(0,220,297,430))
        self.assertEqual(result[0]['box'][1],228)

    def test_no_photo_is_silently_omitted(self):
        self.assertEqual(len(arrange(self.records(100),self.page)),100)

    def test_invalid_sizes(self):
        for values in [(0,1,1,1),(1,1,float('nan'),10),(1,1,-1,10)]:
            with self.assertRaises(ValueError):fit_size(*values)

    def test_caption_name_description_and_unicode(self):
        self.assertEqual(caption_text(' F001 ','foto è.jpg',' Ingresso nord '),'F001 — foto è.jpg\nIngresso nord')
        self.assertEqual(caption_text('F001','foto.jpg',''),'F001 — foto.jpg')
        self.assertEqual(caption_text('','foto.jpg','Uno\nDue'),'foto.jpg\nUno\nDue')

if __name__=='__main__':unittest.main()
