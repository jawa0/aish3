import fitz

FILE_PATH = "res/knowledge/pdf/Calculus Made Easy.pdf"

print(f'Opening "{FILE_PATH}"...')

doc = fitz.open(FILE_PATH)
print(f'Document has {len(doc)} pages.')

I_PAGE = 11
ZOOM = 3.0

print(f'Page {I_PAGE}...')
page = doc[I_PAGE]

mat = fitz.Matrix(ZOOM, ZOOM)
pix = page.get_pixmap(matrix=mat)
print(f'Page size: {pix.width}, {pix.height}')
pix.save(f'page-{I_PAGE:03}_zoom_{ZOOM}.png')
