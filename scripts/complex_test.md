# Complex Character Style Test

Here is a paragraph testing all standard markdown inline formatting:
This text contains **bold**, *italic*, and ***bold italic*** words. 
It also has some ~~strikethrough~~ text, and a [hyperlink to GitHub](https://github.com/studiohelioripple). 
Here is a bit of `inline code` for good measure.

Now, let's test HTML-based character styles supported by Forma:
This text has an <u>underline</u> and a <mark>yellow highlight</mark>.

Finally, let's test dynamic color rendering and the auto-standardization of direct formatting overrides:
- Here is <span style="color: #FF3366">Pink Text</span>.
- Here is <span style="background-color: #00FFCC">Cyan Background Text</span>.
- Here is <span style="color: #FFFFFF; background-color: #000000">Inverted Text (White on Black)</span>.
- Here is a custom named span: <span class="VIPBadge">VIP Member Badge</span>.

> Block quotes should also support **inline styles** perfectly.

```python
# Code blocks should remain unaffected by span injection
print("Hello <span style='color:red'>World</span>")
```
