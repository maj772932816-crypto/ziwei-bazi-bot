# narrative.json 结构

`zwbz.py render facts.json narrative.json -o report.html` 读取这个文件。所有字段都可以省略，省略的部分报告里就不显示；文字一律是纯文本（不要写 HTML 或 Markdown），段落之间用 `\n` 分隔。完整示例见 `example-narrative.json`（虚构的命盘）。

```jsonc
{
  "headline": "天机天梁坐命 · 乙木生巳月",          // 报告大标题：紫微命宫特征 · 八字日主与月令
  "title": "机梁坐命命格分析",                      // 浏览器标签名，2–6 个字的名字，可省略
  "summary": [                                       // 结论速览，4–6 张卡片
    {"title": "事业", "text": "一两句话。", "agree": "两边一致"}  // agree：两边一致 | 只有八字 | 只有紫微 | 有分歧 | 已核对
  ],
  "bazi": {
    "strength_label": "偏弱",                        // 旺衰结论（可与程序参考标签不同，正文说明理由）
    "strength": "旺衰的理由，一段。",
    "pattern": "格局的判断，一段。",
    "xiji": [{"level": "首要喜用", "wuxing": "水（印）", "why": "理由"}],  // level：首要喜用 | 次喜 | 适量 | 忌
    "personality": "…", "career": "…", "wealth": "…", "health": "…",
    "relatives": [{"who": "母亲", "text": "…"}],
    "dayun": {"丁丑": "这步大运的要点"}               // 键为大运干支，与 facts 一致
  },
  "ziwei": {
    "ming": "命宫…", "shen": "身宫…", "sanfang": "三方四正…",
    "patterns": [{"name": "善荫朝纲", "status": "成立情况和依据"}],
    "palaces": [{"palace": "夫妻（甲申）", "text": "…"}],
    "daxian": {"35-44": "这个大限的要点"}           // 键为「起-止」虚岁，与 facts 一致
  },
  "cross": [{"topic": "事业方向", "bazi": "…", "ziwei": "…", "agree": "高"}],   // agree：高 | 中 | 低
  "years": {"2026": "这一年的提示"},                 // 键为公历年份字符串，与 facts.years 对应
  "months": [{"label": "11 月（公历）", "text": "这个月的提示"}],   // 只有 run --months 或 month --save 之后才显示
  "checklist": [{"text": "可以核对的过去事件", "basis": "依据"}],
  "advice": [{"title": "事业", "text": "…"}]
}
```

写完后先运行 `zwbz lint facts.json narrative.json`：它会确认 JSON 合法，并核对解读里的命理事实；错误改到 0 再 `zwbz render`。

## 合盘解读（`zwbz render-match match.json narrative.json`，范例见 `example-match-narrative.json`）

```jsonc
{
  "headline": "两个人的合盘标题",
  "summary": [{"title": "相处的底色", "text": "…", "agree": "两边一致"}],
  "bazi": "八字对照的解读，一到两段，用 \n 分段",
  "ziwei": "紫微对照的解读，一到两段",
  "strengths": ["合得来的地方，每条写依据"],
  "frictions": ["要磨合的地方，每条写依据"],
  "advice": ["具体的相处建议"]
}
```
