"""Build a deliberately hostile mock page around the WordPress fragment.

Run after `build_singlefile.py`:

    python build_singlefile.py && python test_embed.py

then open `_embed_test.html`. The fake theme above uses bare-element rules
with !important, a Georgia body font and `box-sizing: content-box` — the
fragment must render identically to the standalone site while leaving the
page's own h1/paragraphs untouched.
"""

import pathlib

root = pathlib.Path(r"C:\Users\Boris\Downloads\New folder\dfg-dashboard")
frag = (root / "dist" / "dfg-dashboard-wordpress.html").read_text(encoding="utf-8")

# deliberately hostile "theme": bare-tag rules, generic classes, box-sizing reset
page = """<!doctype html>
<html lang="mk">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Тест страница со тема</title>
<style>
  /* --- fake WordPress theme --- */
  * { box-sizing: content-box; }
  body { margin: 40px; font-family: Georgia, "Times New Roman", serif;
         background: #fdf6e3; color: #333; font-size: 18px; }
  h1 { font-family: Georgia, serif; color: #8b0000; font-size: 44px; }
  h2, h3 { font-family: Georgia, serif; color: #8b0000 !important;
           font-size: 34px !important; letter-spacing: 5px;
           text-transform: uppercase; border-bottom: 4px double #8b0000; }
  p { line-height: 2.1; text-align: justify; }
  button { font-family: Georgia, serif; font-size: 20px !important;
           background: #ffe !important; border: 3px outset #999 !important;
           color: #000 !important; padding: 12px 18px !important;
           border-radius: 0 !important; margin: 3px; }
  select { font-size: 20px; padding: 10px; }
  ul { list-style: square outside; }
  li { margin: 12px 0; }
  .container { max-width: 900px; margin: 0 auto; }
</style>
</head>
<body>
<div class="container">
  <h1>Наслов на страницата</h1>
  <p>Воведен текст кој го поседува темата. Ова е обичен параграф.</p>

  <!-- ====== WordPress Custom HTML block starts here ====== -->
FRAGMENT
  <!-- ====== WordPress Custom HTML block ends here ====== -->

  <p>Заклучок на страницата.</p>
</div>
</body>
</html>
"""

out = page.replace("FRAGMENT", frag)
(root / "_embed_test.html").write_text(out, encoding="utf-8")
print("wrote _embed_test.html", len(out))
