// 交叉核对：用 lunar-javascript 和 iztro 独立再算一遍农历、八字和紫微盘。
// 用法：node crosscheck.cjs cases.json > out.json
// cases.json：[{id, bazi_time: "当地时间 YYYY-MM-DD HH:MM", bazi_time_bj?: "北京时间表示的出生时刻", ziwei_date: "YYYY-MM-DD", hour_idx: 0-11, gender: "male"|"female", zi_sect: "next"|"same", horoscope_dates?: ["YYYY-MM-DD"]}]
// 依赖：在本目录 npm install（见 package.json：lunar-javascript、iztro）
const fs = require('fs');
const { Solar } = require('lunar-javascript');
const { astro } = require('iztro');

astro.config({ yearDivide: 'normal' }); // 紫微按正月初一换年

const cases = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const out = [];
for (const c of cases) {
  const r = { id: c.id };
  try {
    // 日柱、时柱看当地（真太阳）时间；年柱、月柱、起运看出生瞬间与节气的先后，用北京时间表示的出生时刻
    const eightChar = s => {
      const [d, hm] = s.split(' ');
      const [Y, M, D] = d.split('-').map(Number);
      const [h, m] = hm.split(':').map(Number);
      const ec = Solar.fromYmdHms(Y, M, D, h, m, 0).getLunar().getEightChar();
      ec.setSect(c.zi_sect === 'same' ? 2 : 1);
      return ec;
    };
    const ecLocal = eightChar(c.bazi_time);
    const ecInstant = eightChar(c.bazi_time_bj || c.bazi_time);
    r.pillars = [ecInstant.getYear(), ecInstant.getMonth(), ecLocal.getDay(), ecLocal.getTime()];
    const yun = ecInstant.getYun(c.gender === 'male' ? 1 : 0, 2);
    r.yun_start = yun.getStartSolar().toYmd();
    r.dayun = yun.getDaYun().slice(1, 9).map(x => x.getGanZhi());
  } catch (e) { r.bazi_error = String(e); }
  try {
    const [Y, M, D] = c.ziwei_date.split('-').map(Number);
    const l = Solar.fromYmd(Y, M, D).getLunar();
    r.lunar = { year: l.getYear(), month: Math.abs(l.getMonth()), day: l.getDay(), leap: l.getMonth() < 0 };
    const a = astro.bySolar(`${Y}-${M}-${D}`, c.hour_idx, c.gender === 'male' ? '男' : '女', true, 'zh-CN');
    r.ziwei = {
      soul: a.earthlyBranchOfSoulPalace, body: a.earthlyBranchOfBodyPalace, ju: a.fiveElementsClass,
      mingzhu: a.soul, shenzhu: a.body,
      palaces: a.palaces.map(p => ({
        branch: p.earthlyBranch, stem: p.heavenlyStem, name: p.name, body: p.isBodyPalace,
        stars: [...p.majorStars, ...p.minorStars, ...p.adjectiveStars].map(s => s.name),
        hua: Object.fromEntries([...p.majorStars, ...p.minorStars].filter(s => s.mutagen).map(s => [s.name, s.mutagen])),
        decadal: p.decadal.range, ages: p.ages.slice(0, 3),
        cs: p.changsheng12, bs: p.boshi12, jq: p.jiangqian12, sq: p.suiqian12,
      })),
    };
    // 运限：某些日期的大限、流年、小限、流月（iztro）与八字流月（lunar-javascript，按节气）
    const BR = '子丑寅卯辰巳午未申酉戌亥';
    const br = i => BR[(i + 2) % 12]; // iztro 宫位序号 0 = 寅
    r.horoscope = (c.horoscope_dates || []).map(ds => {
      const [y, m, d] = ds.split('-').map(Number);
      const h = a.horoscope(`${y}-${m}-${d}`, c.hour_idx);
      return {
        date: ds, decadal: br(h.decadal.index), decadal_stem: h.decadal.heavenlyStem,
        yearly: br(h.yearly.index), yearly_gz: h.yearly.heavenlyStem + h.yearly.earthlyBranch,
        monthly: br(h.monthly.index), monthly_gz: h.monthly.heavenlyStem + h.monthly.earthlyBranch,
        monthly_mutagen: h.monthly.mutagen, age: br(h.age.index), nominal_age: h.age.nominalAge,
        bazi_month: Solar.fromYmdHms(y, m, d, 12, 0, 0).getLunar().getMonthInGanZhiExact(),
      };
    });
  } catch (e) { r.ziwei_error = String(e); }
  out.push(r);
}
process.stdout.write(JSON.stringify(out));
