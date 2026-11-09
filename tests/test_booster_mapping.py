import sys,unittest,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from booster_mapping import model_sources,COURSE_CODES

class ModelMappingTests(unittest.TestCase):
    def rows(self):
        return [{'key':'donor_'+str(n),'resources':[{'models':['CausticsArea','Cnsw_%d%d'%((n-1)//8+1,(n-1)%8+1)]}]} for n in range(1,49)]
    def test_shuffled_donors_follow_models(self):
        rows=self.rows()[::-1];r=model_sources(rows)
        self.assertEqual((r[12],r[20],r[48]),('donor_12','donor_42','donor_48'))
    def test_console_observed_production_order(self):
        r=model_sources(self.rows())
        self.assertEqual((r[18],r[22],r[26],r[31]),('donor_19','donor_18','donor_31','donor_22'))
        self.assertEqual((r[33],r[40],r[45]),('donor_45','donor_41','donor_33'))
        self.assertEqual((r[32],r[37]),('donor_29','donor_32'))
        self.assertEqual(len(set(COURSE_CODES)),48)
    def test_missing_or_duplicate_model_rejected(self):
        with self.assertRaises(ValueError):model_sources(self.rows()[:-1])
        rows=self.rows();rows[-1]=copy.deepcopy(rows[0])
        with self.assertRaises(ValueError):model_sources(rows)
    def test_ambiguous_and_invalid_models_rejected(self):
        rows=self.rows();rows[0]['resources'][0]['models']+=['Cnsw_12']
        with self.assertRaises(ValueError):model_sources(rows)
        rows=self.rows();rows[0]['resources'][0]['models']=['Cnsw_10']
        with self.assertRaises(ValueError):model_sources(rows)

if __name__=='__main__':unittest.main()
