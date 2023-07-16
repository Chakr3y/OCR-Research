from fitz import Rect

# ScanArea provides a template for saving individual
# scanned regions within a scan "format".
class ScanArea:
	def __init__(self, page:int, p1:tuple, p2:tuple):
		self.page = page
		self.p1 = p1
		self.p2 = p2

	def __init__(self, page:int, rect:Rect):
		self(page, rect.tl, rect.br)
    
	@property
	def rect(self):
		return Rect(self.p1, self.p2)
    