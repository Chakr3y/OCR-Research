from typing import overload
from fitz import Rect, Point

# ScanArea provides a template for saving individual
# scanned regions within a scan "format".
class ScanArea:
	@overload
	def __init__(self, page: int, rect: Rect) -> None:
		...
	@overload
	def __init__(self, page: int, p1: tuple|Point, p2: tuple|Point) -> None:
		...
	def __init__(self, page: int, p1, p2=None):
		self.page = page

		# if first overload, convert rect coords to points
		if isinstance(p1, Rect): #and p2 == None?
			p2 = p1.br
			p1 = p1.tl
		
		self.p1: tuple = p1 if isinstance(p1, tuple) else (p1.x, p1.y)
		self.p2: tuple = p2 if isinstance(p2, tuple) else (p2.x, p2.y)
    
	@property
	def rect(self):
		return Rect(self.p1, self.p2)

# class for grouping ScanAreas into Formats
class Format():
	_areas: list[ScanArea]

	def __init__(self, name: str = None, lang: str = 'eng'):
		self.name = name
		self._areas = []
		self.lang = lang

	def append(self, value: ScanArea):
		self._areas.append(value)

	def __getitem__(self, key):
		return self._areas[key]
	
	def __setitem__(self, key, value: ScanArea):
		self._areas[key] = value
	
	def __delitem__(self, key):
		del self._areas[key]

	def __len__(self):
		return len(self._areas)