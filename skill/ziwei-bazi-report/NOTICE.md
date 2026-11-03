# 许可与第三方来源

## 本技能

本技能的代码和文档以 MIT 许可发布：

```
MIT License

Copyright (c) 2026 ziwei-bazi-report contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 随包数据

`scripts/zwbz/data/` 里的城市经度表（cities.json）、中国夏令时表（dst_cn.json）、《紫微斗数全书》主星亮度表（brightness_qs.json）整理自开源项目 [Renhuai123/ziwei-doushu](https://github.com/Renhuai123/ziwei-doushu) 的 `lib/ziwei/cities.ts`、`dst-cn.ts`、`school-data.ts`，原项目代码以 MIT 许可发布：

```
MIT License

Copyright (c) 2026 紫微研究

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 运行时下载、不随包分发

- 紫微斗数开源解读数据集 v4.0：CC BY 4.0，使用时须署名「紫微斗数开源解读数据集 v4.0，来源 https://github.com/Renhuai123/ziwei-doushu ，作者 王多鱼AI」；报告会自动写入。数据集正文引用的倪海厦原话不在其授权范围内，仅限非商业的学习研究。
- iztro、lunar-javascript（npm，MIT）；ephem（pip，LGPL-3.0）；zstandard（pip，BSD）。
