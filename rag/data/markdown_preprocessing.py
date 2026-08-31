
import pymupdf4llm
import re
import fitz


manual_path="./documents/manual.pdf"
# doc=fitz.open(manual_path)
# print("-> opened the file")

# markdown_content=pymupdf4llm.to_markdown(
#     manual_path,
#     pages=range(7,len(doc))
# )
# print("-> manual loaded as markdown")

# with open("./documents/markdown_manual.md","w",encoding="utf-8") as file:
#     file.write(markdown_content)
# print("-> markdown file saved")

# print("-> readed the markdown file")

# with open("./documents/markdown_manual.md","r",encoding="utf-8") as file:
#     raw_markdown_content= file.read()

# # Replacing the page headers with only the page number
# pattern1=(
#     r"\|*Doc\..*?"
#     r"\|+Page.*?"
#     r"(?P<nb_page>\d+)"
#     r".*?73\|"
# )

# pattern2=r"# \*\*MAINTENANCE MANUAL\*\* "

# pattern3=r"\*\*�\*\*"

# pattern4=(
#     r"[\|]*[\s*]*(?:Check list|C l|Chk lit)[\s*]*\|.*?"
#     r"\*\*Annually\*\*\|"
# )

# pattern5=r"�"

# def replace_with_page_number(match):
#     page_number=match.group("nb_page")
#     return f'{{\"page\":{page_number}}}'

# def replace_with_none(math):
#     return ""

# def replace_with_x(match):
#     return "x"

# def replace_checklist_tab_header(match):
#     return (
#         "| **Check list** | **Inspection Interval** | | | | |\n"
#         "|---|---|---|---|---|---|\n"
#         "| | **At each visit** | **Monthly** | **3 Monthly** | **Semi annually** | **Annually** |"
#     )

# def replace_with_space(match):
#     return ' ' 

# print("-> cleanning ...")    
# patterns=[pattern1,pattern2,pattern3,pattern4,pattern5]
# replacements=[
#     replace_with_page_number,
#     replace_with_none,
#     replace_with_x,
#     replace_checklist_tab_header,
#     replace_with_space
# ]
# clean_markdown=raw_markdown_content
# for i in range(len(patterns)):
#     clean_markdown=re.sub(
#         patterns[i],
#         replacements[i],
#         clean_markdown,
#         flags=re.DOTALL
#     )
# with open("./documents/cleaned_markdown_manual.md","w",encoding="utf-8") as file:
#     file.write(clean_markdown)
# print("-> cleaned markdown file saved")

# Manual cleaning
 #-------------------------
 
#Strinping the text
print("-> loading the cleaned markdawn content")
manual_path="./documents/cleaned_markdown_manual_v2.md"
with open(manual_path,"r",encoding="utf-8") as file:
    clean_markdown_content=file.read()
clean_markdown_content=re.sub(r'\n{2,}','\n\n',clean_markdown_content)
print("-> writing the striped markdawn file")
with open("./documents/cleaned_markdown_manual_v3.md","w",encoding="utf-8") as file:
    file.write(clean_markdown_content);

print("done")