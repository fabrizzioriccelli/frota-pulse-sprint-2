// Executa o projeto no wokwi.com (compilação real para ESP32 no servidor do Wokwi), provoca cada alerta pelos
// controles do circuito e grava: vídeo da tela, capturas e o texto do Monitor Serial.
// Não precisa de conta no Wokwi (o projeto é carregado num projeto novo, sem salvar).
//
// Uso (Node.js 18+ e Playwright com Chromium):
//   node src/esp32/wokwi/executar_no_wokwi.js docs/evidencias/wokwi
// O argumento é a pasta de saída. Com "teste" como segundo argumento, só calibra os potenciômetros.
const { chromium } = require('playwright');
const fs = require('fs'); const path = require('path');
const FW = path.resolve(__dirname, '..', 'firmware', 'telemetria_frota');
const DIAG = path.join(__dirname, 'diagram.json');
const OUT = process.argv[2] || 'saida'; fs.mkdirSync(OUT, { recursive: true });
const marcos = []; let T0 = 0;
const marca = (nome) => { const t = (Date.now() - T0) / 1000; marcos.push({ t, nome }); console.log(t.toFixed(1), nome); };
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1600, height: 900 }, recordVideo: { dir: path.join(OUT, 'video'), size: { width: 1600, height: 900 } } });
  const p = await ctx.newPage(); T0 = Date.now();
  await p.goto('https://wokwi.com/projects/new/esp32', { waitUntil: 'domcontentloaded', timeout: 90000 });
  await p.waitForFunction(() => window.monaco && monaco.editor.getModels().some(m => m.uri.toString().includes('sketch.ino')), null, { timeout: 90000 });
  await p.waitForTimeout(3000);
  await p.mouse.click(355, 64); await p.waitForTimeout(500);
  const [fc] = await Promise.all([p.waitForEvent('filechooser'), p.getByText('Upload file(s)...').click()]);
  await fc.setFiles(['limites.h', 'perfil.h', 'perfis_demo.h'].map(f => path.join(FW, f)));
  await p.waitForTimeout(1500);
  await p.evaluate(t => monaco.editor.getModels().find(m => m.uri.toString().includes('sketch.ino')).setValue(t), fs.readFileSync(path.join(FW, 'telemetria_frota.ino'), 'utf8'));
  await p.getByText('diagram.json', { exact: true }).first().click(); await p.waitForTimeout(1200);
  await p.evaluate(t => monaco.editor.getModels().find(m => m.uri.toString().includes('diagram.json')).setValue(t), fs.readFileSync(DIAG, 'utf8'));
  await p.waitForTimeout(2500);
  await p.getByText('sketch.ino', { exact: true }).first().click(); await p.waitForTimeout(800);
  // enquadrar o circuito
  await p.getByLabel('Zoom, grid, and more').click(); await p.waitForTimeout(600);
  const itens = await p.evaluate(() => [...document.querySelectorAll('[role=menuitem], li')].map(x => x.innerText.trim()).filter(Boolean));
  console.log('menu zoom:', itens.join(' | '));
  const fit = itens.find(x => /fit|ajust/i.test(x));
  if (fit) await p.locator('li', { hasText: /^Fit/ }).first().click({ timeout: 5000 }).catch(() => {});
  await p.waitForTimeout(500); if (await p.$('.MuiPopover-root')) await p.keyboard.press('Escape');
  await p.waitForTimeout(800);
  await p.screenshot({ path: path.join(OUT, '01_projeto_carregado.png') });
  marca('projeto carregado');
  await p.getByLabel('Start the simulation').click(); marca('clique em iniciar (compilação)');
  const ok = await p.waitForFunction(() => document.body.innerText.includes('timestamp_s,veiculo_id') || document.body.innerText.includes('Build failed'), null, { timeout: 300000 }).then(() => true).catch(() => false);
  if (!ok || (await p.evaluate(() => document.body.innerText.includes('Build failed')))) {
    await p.screenshot({ path: path.join(OUT, 'erro.png') }); console.log(await p.evaluate(() => document.body.innerText.slice(-3000)));
    await ctx.close(); await b.close(); process.exit(1);
  }
  marca('simulação iniciada');
  const pots = async () => p.$$('wokwi-potentiometer'); const slide = async () => p.$('wokwi-slide-potentiometer');
  // gira o potenciômetro arrastando o botão com o mouse até a fração f do curso (-135° a +135°)
  const girar = async (el, f) => {
    const bb = await el.boundingBox(); const cx = bb.x + bb.width / 2, cy = bb.y + bb.height * 0.42;
    const ang = (-135 + 270 * f) * Math.PI / 180, r = bb.width * 0.3;
    await p.mouse.move(cx, cy - 4); await p.mouse.down();
    for (let k = 1; k <= 12; k++) { const a = (-0 + ang * k / 12); await p.mouse.move(cx + r * Math.sin(a), cy - r * Math.cos(a)); await p.waitForTimeout(25); }
    await p.mouse.up();
  };
  // arrasta o cursor do potenciômetro deslizante até a fração f do curso
  const deslizar = async (el, f) => {
    const bb = await el.boundingBox(); const y = bb.y + bb.height / 2;
    const atual = el._frac ?? await el.evaluate(e => Number(e.value) / 1023); el._frac = f;
    const x0 = bb.x + bb.width * 0.08, x1 = bb.x + bb.width * 0.92;
    await p.mouse.move(x0 + (x1 - x0) * atual, y); await p.mouse.down();
    for (let k = 1; k <= 12; k++) { await p.mouse.move(x0 + (x1 - x0) * (atual + (f - atual) * k / 12), y); await p.waitForTimeout(25); }
    await p.mouse.up();
  };
  if (process.argv[3] === 'teste') {
    const ultima = async () => p.evaluate(() => { const l = document.body.innerText.trim().split('\n').filter(x => /^\d+,B-V/.test(x)); return l[l.length - 1]; });
    await p.waitForTimeout(4000); console.log('inicial', await ultima());
    const [, pr, pt] = await pots();
    console.log('caixa pot', JSON.stringify(await pr.boundingBox()), 'caixa slide', JSON.stringify(await (await slide()).boundingBox()));
    for (const f of [1, 0.5, 0.1]) { await girar(pr, f); await p.waitForTimeout(3000); console.log('rpm', f, await ultima()); }
    await girar(pt, 1); await p.waitForTimeout(3000); console.log('temp 1', await ultima());
    for (const f of [0.05, 0.9]) { await deslizar(await slide(), f); await p.waitForTimeout(3000); console.log('comb', f, await ultima()); }
    await p.screenshot({ path: path.join(OUT, 'teste.png') });
    await ctx.close(); await b.close(); return;
  }
  const ajustar = async (el, v) => p.evaluate(([e, v]) => { e.value = v; e.dispatchEvent(new InputEvent('input', { bubbles: true })); }, [el, v]);
  const apertar = async (i) => { const bt = (await p.$$('wokwi-pushbutton'))[i]; const bb = await bt.boundingBox();
    await p.mouse.move(bb.x + bb.width / 2, bb.y + bb.height / 2); await p.mouse.down(); await p.waitForTimeout(600); await p.mouse.up(); };
  const foto = async (n) => p.screenshot({ path: path.join(OUT, n) });
  await p.waitForTimeout(7000); await foto('02_normal.png'); marca('modo SENSORES: leituras normais, LED verde');
  const [pv, pr, pt] = await pots(); const sl = await slide();
  await girar(pr, 1); marca('rotação no máximo: RPM_ALTO, LED amarelo'); await p.waitForTimeout(6000); await foto('03_rpm_alto.png');
  await girar(pt, 1); marca('temperatura 120 °C: TEMP_ALTA, LED vermelho e buzzer'); await p.waitForTimeout(6000); await foto('04_critico_temp_rpm.png');
  await girar(pr, 0.45); await girar(pt, 0.55); marca('rotação e temperatura normalizadas'); await p.waitForTimeout(5000);
  await girar(pv, 0.95); marca('velocidade acima de 110 km/h: VEL_EXCESSO'); await p.waitForTimeout(6000); await foto('05_velocidade.png');
  await girar(pv, 0.35); marca('velocidade normalizada'); await p.waitForTimeout(3000);
  await deslizar(sl, 0.05); marca('combustível abaixo de 15%: COMB_BAIXO'); await p.waitForTimeout(6000); await foto('06_combustivel.png');
  await apertar(0); marca('botão Modo: ROTEIRO'); await p.waitForTimeout(20000); await foto('07_roteiro_B-V23.png');
  await apertar(1); marca('botão Veículo: B-V12'); await p.waitForTimeout(20000); await foto('08_roteiro_B-V12.png');
  await apertar(1); marca('botão Veículo: C-V07'); await p.waitForTimeout(15000); await foto('09_roteiro_C-V07.png');
  const serial = await p.evaluate(() => {
    let melhor = null;
    document.querySelectorAll('*').forEach(e => { const t = e.innerText || ''; if (t.includes('timestamp_s,veiculo_id') && (!melhor || t.length < melhor.length)) melhor = t; });
    return melhor;
  });
  fs.writeFileSync(path.join(OUT, 'monitor_serial_wokwi.txt'), serial || '');
  fs.writeFileSync(path.join(OUT, 'marcos.json'), JSON.stringify(marcos, null, 1));
  marca('fim'); await ctx.close(); await b.close();
})();
