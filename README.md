# 紫微八字命理师

给 Grok Bot（以及任何能运行命令的 AI 助手）用的技能：输入出生信息，自动排紫微斗数和八字命盘，多来源交叉核对，查开源的 13 维解读数据集，由 AI 写解读，程序再检查解读有没有说错，最后生成可以微信转发的报告。

## 能做什么

| 功能 | 命令 | 说明 |
|---|---|---|
| 排盘 | `run` | 农历换算、八字（四柱、十神、藏干、纳音、神煞、旺衰计分、大运起运、合冲刑害）、紫微全盘（14 主星、六吉六煞、杂曜、全书亮度、生年四化、宫干自化、大限小限）、逐年表；处理真太阳时、中国夏令时、晚子时、闰月 |
| 交叉核对 | `run` 自动做 | 用 lunar-javascript 和 iztro 独立重算，逐项比对；不一致就停下 |
| 13 维数据集 | `run` 自动做 | 查[紫微斗数开源解读数据集 v4.0](https://github.com/Renhuai123/ziwei-doushu)（1950–2026 年出生），下载时按官方 SHA256 校验 |
| 检查解读 | `lint` | 核对 AI 写的解读里提到的四化（含自化来源）、星曜落宫、亮度、年份干支、大运大限（含年份段属于哪一边）、四柱等是否和排盘一致，并查恐吓、绝对化的写法 |
| 检查聊天回复 | `lint-text` | 报告前的结论段、流年流月等追问的回答、合盘回复，发出前用同样的规则检查 |
| 出报告 | `render` | 单文件 HTML（离线可开、可转发）、Markdown、聊天短摘要三种格式 |
| 流月 | `month` | 某一天或整年：八字节气月、紫微流月（流年斗君起正月） |
| 合盘 | `match`、`render-match` | 两人的日干、配偶宫、生肖、五行互补、命宫，以及生年四化互入；合盘解读同样先检查（`lint-match`） |
| 定时辰 | `hours` | 出生时间不确定时，把候选时辰并排对照 |
| 删除数据 | `purge` | 用户要求时删除对应的工作目录 |

## 准确性

| 核对内容 | 结果 |
|---|---|
| 农历换算，1950–2030 年每一天 | 29,585 / 29,585 天与 lunar-javascript 一致（含 29 个闰月） |
| 八字四柱 | 3,000 张随机盘与 lunar-javascript 一致 |
| 紫微全盘：每颗星的落宫、四化、长生 / 博士 / 将前 / 岁前十二神、大限、小限 | 6,500 多张随机盘与 iztro 一致 |
| 运限：大限、流年、小限、虚岁、流月命宫、流月干支、流月四化、八字流月 | 1,500 张盘、约 9,000 个日期与 iztro、lunar-javascript 一致 |
| 节气时刻 | 与 lunar-javascript 节气表相差不到 1 分钟 |
| 一张真实命盘对照主流排盘 App 截图 | 122 / 122 项一致，主星亮度 14 / 14 |

出生时刻离节气只有几秒时，不同算法会有几秒差异；程序会提示「离节气交界很近」，并以出生证明的精确时间为准。

## 用在 Grok Bot 上

看 [grok/上线步骤.md](grok/上线步骤.md)。简单说：在 Releases 发布程序 → 新建 Bot，发送 [grok/BOT说明.md](grok/BOT说明.md) → 把 `dist/SKILL.md` 保存为技能 → Bot 第一次用时会自动下载、校验、安装 → 分享模板。

## 在命令行用

```bash
cd skill/ziwei-bazi-report/scripts
bash install.sh                                    # Python 3.9+、Node.js 18+
bash zwbz.sh run --date 1990-05-20 --time 14:30 --gender 女 --city 杭州 --out work/demo
bash zwbz.sh lint work/demo/facts.json ../references/example-narrative.json
bash zwbz.sh render work/demo/facts.json ../references/example-narrative.json
```

`bash zwbz.sh --help` 看全部命令。AI 写解读的规则见 [references/analysis-guide.md](skill/ziwei-bazi-report/references/analysis-guide.md)。

## 目录

```
skill/ziwei-bazi-report/   技能本体：SKILL.md、scripts/（排盘引擎和命令行）、references/（写作指南、结构、范例）
grok/                      Grok Bot 的职责说明和上线步骤
tools/make_release.py      生成发布包、SHA256 和填好下载地址的技能文字
tests/regression.py        回归测试（虚构出生信息，结果与 golden.json 比对）
```

## 维护

```bash
python3 tests/regression.py                      # 回归测试
bash skill/ziwei-bazi-report/scripts/zwbz.sh selftest --n 200   # 随机盘对拍
python3 tools/make_release.py --repo 用户名/仓库名               # 发布
```

改了排盘口径，先跑对拍确认无误，再 `python3 tests/regression.py --update`。

## 许可与来源

- 代码：MIT，见 [LICENSE](LICENSE)。
- 城市经度、中国夏令时、《全书》亮度表整理自 [Renhuai123/ziwei-doushu](https://github.com/Renhuai123/ziwei-doushu)（MIT），详见 [NOTICE](skill/ziwei-bazi-report/NOTICE.md)。
- 13 维解读数据集：CC BY 4.0，作者 王多鱼AI；报告会自动署名。数据集正文引用的倪海厦原话仅限非商业用途。

## 免责

命理是传统文化里的一套解释体系，没有科学证据表明它能预测具体事件。本工具按传统规则推演，结果仅供参考，不能替代医疗、法律、财务和婚恋方面的专业判断。
