项目依赖 `poppler-windows` ，下载 URL：
https://github.com/oschwartz10612/poppler-windows/releases/download/v25.12.0-0/Release-25.12.0-0.zip
下载后解压后，移动 `poppler-25.12.0` 到 `./pharma_card_extractor` 下，最终的目录结构应该类似：

```terminaloutput
.
├─README.md
├─ ...
└─pharma_card_extractor
    ├─1_split_pdf.py
    ├─...
    └─poppler-25.12.0 <- 位置在这里
       ├─Library
       │  ├ ...
       │  └─bin
       └─share
```