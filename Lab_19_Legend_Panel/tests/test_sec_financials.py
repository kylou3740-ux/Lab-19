import unittest
from sec_financials import calculate_checks, calculate_panel_checks, calculate_revenue_cagr, find_unprinted_numbers

class Checks(unittest.TestCase):
 def test_buffett_three_pass(self):
  rows=[{"roe_pct":20,"owner_earnings":100},{"roe_pct":17,"owner_earnings":120}]
  self.assertEqual(calculate_checks(rows),{"roe_15_percent_every_year":"pass","owner_earnings_positive_every_year":"pass","owner_earnings_grew_first_to_last":"pass"})
 def test_missing_owner_earnings_unknown(self):
  rows=[{"roe_pct":20,"owner_earnings":None},{"roe_pct":17,"owner_earnings":None}]
  c=calculate_checks(rows); self.assertEqual(c["owner_earnings_positive_every_year"],"not known"); self.assertEqual(c["owner_earnings_grew_first_to_last"],"not known")
 def test_costco_published_revenue_cagr(self):
  rev=[226954,242290,254453,275235,303154]
  rows=[{"revenue":x} for x in rev]
  self.assertAlmostEqual(calculate_revenue_cagr(rows),7.51,places=2)
 def test_cagr(self):
  rows=[{"revenue":100},{"revenue":110},{"revenue":120},{"revenue":130},{"revenue":140}]
  self.assertAlmostEqual(calculate_revenue_cagr(rows),((1.4)**.25-1)*100)
 def test_costco_expected_pattern(self):
  rows=[{"net_income":100,"operating_cash_flow":110,"owner_earnings":90,"liabilities_to_equity":2.11,"roe_pct":20,"revenue":1000,"research_and_development":None} for _ in range(5)]
  rows[-1]["revenue"]=1325.6; rows[-1]["liabilities_to_equity"]=1.49
  c=calculate_panel_checks(rows)
  self.assertEqual(c["buffett"]["roe_15_percent_every_year"],"pass")
  self.assertEqual(c["cathie_wood"]["revenue_growth_15_percent_first_to_last"],"fail")
  self.assertEqual(c["cathie_wood"]["research_and_development_5_percent_latest_year"],"not known")
  self.assertEqual(c["burry"]["liabilities_no_more_than_2x_equity_latest_year"],"pass")
 def test_missing_data_stays_unknown(self):
  rows=[{"net_income":None,"operating_cash_flow":None,"owner_earnings":None,"liabilities_to_equity":None,"roe_pct":None,"revenue":None,"research_and_development":None} for _ in range(5)]
  c=calculate_panel_checks(rows); self.assertEqual(c["burry"]["operating_cash_flow_at_least_net_income_every_year"],"not known"); self.assertEqual(c["cathie_wood"]["revenue_growth_15_percent_first_to_last"],"not known")
 def test_unprinted_number(self):
  self.assertIn("40.0",find_unprinted_numbers("ROE 40.0%","ROE 28.3"))
  self.assertEqual(find_unprinted_numbers("ROE 28.3%","ROE 28.3"),[])
if __name__=="__main__": unittest.main()
