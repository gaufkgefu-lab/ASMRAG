# 本地向量知识库

这个目录里的脚本会把 `D:\python\zhishiku` 下的 `.txt` 文件构建成一个本地可检索的向量知识库。

当前实现特点：

- 不依赖第三方 Python 包
- 直接支持当前的 `zhishiku` 文本目录
- 对 `tupu.txt` 按表格行建库
- 对长篇书籍正文按段落切块建库
- 使用中文字符级 n-gram TF-IDF 做本地向量检索

## 构建知识库

```powershell
python D:\python\build_zhishiku_kb.py
```

或者：

```powershell
python D:\python\vector_kb.py build --source D:\python\zhishiku --output D:\python\zhishiku_kb
```

构建后会生成：

- `D:\python\zhishiku_kb\index.json`
- `D:\python\zhishiku_kb\summary.json`

## 查询知识库

```powershell
python D:\python\vector_kb.py search --index D:\python\zhishiku_kb\index.json --query "污泥膨胀怎么处理"
```

## 说明

这是一版“本地零依赖可运行”的向量库方案，适合先把资料变成可搜索知识库。

如果后面你希望进一步升级效果，可以再替换成：

- 中文 embedding 模型
- FAISS / Chroma
- RAG 问答接口
