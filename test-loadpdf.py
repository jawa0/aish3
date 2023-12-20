import fitz

FILE_PATH = "res/knowledge/pdf/David Flanagan - JavaScript_ The Definitive Guide_ Master the World's Most-Used Programming Language-O'Reilly Media (2020).pdf"

print(f'Opening "{FILE_PATH}"...')

doc = fitz.open(FILE_PATH)
print(f'Document has {len(doc)} pages.')

I_PAGE = 5
ZOOM = 3.0

print(f'Page {I_PAGE}...')
page = doc[I_PAGE]

mat = fitz.Matrix(ZOOM, ZOOM)
pix = page.get_pixmap(matrix=mat)
print(f'Page size: {pix.width}, {pix.height}')
pix.save(f'page-{I_PAGE:03}_zoom_{ZOOM}.png')
