var outlines = document.getElementsByClassName("outline");
var content = outlines[0].innerHTML;
content = content.replace(/&lt;\/?.+?&gt;/g, "");
outlines[0].innerHTML = content;