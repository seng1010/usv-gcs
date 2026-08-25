"""gui_main_node의 웹 대시보드 HTML/JS. 별도 파일로 분리해 노드 코드를 깔끔하게 유지한다."""

INDEX_HTML = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>USV GCS Dashboard</title>
<style>
  body { font-family: sans-serif; background: #111; color: #eee; margin: 0; padding: 16px; }
  h1 { font-size: 18px; margin: 0 0 12px; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .panel { background: #1b1b1b; border: 1px solid #333; border-radius: 8px; padding: 12px; }
  .panel h2 { font-size: 14px; margin: 0 0 8px; color: #9cf; }
  .cams { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; grid-column: span 2; }
  .cams img { width: 100%; background: #000; border-radius: 6px; display: block; }
  .row { display: flex; justify-content: space-between; padding: 2px 0; font-size: 13px; }
  .warn { color: #f66; font-weight: bold; }
  .ok { color: #6f6; }
  .banner { background: #522; color: #fdd; padding: 8px; border-radius: 6px; margin-bottom: 8px; display: none; }
  .bar { background: #333; border-radius: 4px; height: 10px; overflow: hidden; margin-top: 4px; }
  .bar-fill { background: #6c6; height: 100%; }
  .bar-fill.low { background: #e55; }
  button { background: #246; color: #fff; border: none; border-radius: 4px; padding: 6px 12px; cursor: pointer; margin-right: 6px; }
  button:hover { background: #357; }
  input[type=color] { width: 40px; height: 28px; vertical-align: middle; }
</style>
</head>
<body>
<h1>USV Ground Control Station</h1>

<div class="cams">
  <div class="panel">
    <h2>Surface Camera</h2>
    <img id="cam-surface" onerror="this.style.opacity=0.3">
  </div>
  <div class="panel">
    <h2>Underwater Camera</h2>
    <img id="cam-underwater" onerror="this.style.opacity=0.3">
  </div>
</div>

<div class="grid" style="margin-top:12px">
  <div class="panel">
    <h2>Water Quality (/water_quality/data)</h2>
    <div id="wq"></div>
  </div>

  <div class="panel">
    <h2>GPS</h2>
    <div id="gps-banner" class="banner">⚠ GPS 신호 없음 (마지막 위치 유지 중)</div>
    <div id="gps"></div>
  </div>

  <div class="panel">
    <h2>Battery</h2>
    <div id="battery"></div>
  </div>

  <div class="panel">
    <h2>Cmd Vel (조이스틱)</h2>
    <div id="cmdvel"></div>
  </div>

  <div class="panel">
    <h2>Actuator Control</h2>
    <button onclick="setPump(true)">펌프 ON</button>
    <button onclick="setPump(false)">펌프 OFF</button>
    <div style="margin-top:8px">
      LED 색상: <input type="color" id="ledColor" value="#00ff00" onchange="setLed()">
    </div>
  </div>
</div>

<script>
const WEB_VIDEO_PORT = 8080;  // web_video_server 기본 포트, 다르게 실행했다면 여기만 바꾸면 됨
document.getElementById('cam-surface').src =
  `http://${location.hostname}:${WEB_VIDEO_PORT}/stream?topic=/camera/surface/image_raw`;
document.getElementById('cam-underwater').src =
  `http://${location.hostname}:${WEB_VIDEO_PORT}/stream?topic=/camera/underwater/image_raw`;

let lastGoodGps = null;

function batteryBar(pct) {
  const cls = pct < 20 ? 'low' : '';
  return `<div class="bar"><div class="bar-fill ${cls}" style="width:${Math.max(0, Math.min(100, pct))}%"></div></div>`;
}

async function refresh() {
  try {
    const res = await fetch('/api/state');
    const s = await res.json();

    const wq = s.water_quality;
    document.getElementById('wq').innerHTML = wq ? `
      <div class="row"><span>온도</span><span>${wq.temp_c ?? '-'} °C</span></div>
      <div class="row"><span>pH</span><span>${wq.ph ?? '-'}</span></div>
      <div class="row"><span>DO</span><span>${wq.do_mg_l ?? '-'} mg/L</span></div>
      <div class="row"><span>탁도 전압</span><span>${wq.turbidity_voltage_v ?? '-'} V</span></div>
      <div class="row"><span>맑기</span><span>${wq.clarity_pct ?? '-'} % (${wq.clarity_level ?? '-'})</span></div>
    ` : '데이터 없음';

    const banner = document.getElementById('gps-banner');
    if (s.gps_has_fix === false) {
      banner.style.display = 'block';
    } else {
      banner.style.display = 'none';
    }
    if (s.gps_fix) lastGoodGps = s.gps_fix;
    document.getElementById('gps').innerHTML = lastGoodGps ? `
      <div class="row"><span>위도</span><span>${lastGoodGps.latitude.toFixed(6)}</span></div>
      <div class="row"><span>경도</span><span>${lastGoodGps.longitude.toFixed(6)}</span></div>
      <div class="row"><span>Fix</span><span class="${s.gps_has_fix ? 'ok' : 'warn'}">${s.gps_has_fix ? '있음' : '없음 (마지막 위치)'}</span></div>
    ` : 'GPS 데이터 없음';

    const bs = s.battery_status;
    const batteryLabels = {
      thruster1: '추진기1',
      thruster2: '추진기2',
      pump_ctrl: '펌프/제어부',
      sensor_board: '센서 보드',
    };
    let batteryHtml = '';
    if (bs) {
      for (const key of Object.keys(batteryLabels)) {
        const item = bs[key];
        if (!item) continue;
        const pct = item.percentage;
        batteryHtml += `<div class="row"><span>${batteryLabels[key]}</span><span>${item.current_a ?? '-'} A · ${pct ?? '-'}%</span></div>${batteryBar(pct ?? 100)}`;
      }
    }
    document.getElementById('battery').innerHTML = batteryHtml || '데이터 없음';

    document.getElementById('cmdvel').innerHTML = s.cmd_vel ? `
      <div class="row"><span>선속도(x)</span><span>${s.cmd_vel.linear_x.toFixed(2)}</span></div>
      <div class="row"><span>각속도(z)</span><span>${s.cmd_vel.angular_z.toFixed(2)}</span></div>
    ` : '데이터 없음';
  } catch (e) {
    console.error(e);
  }
}

function setPump(on) {
  fetch('/api/pump', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({on})
  });
}

function setLed() {
  const hex = document.getElementById('ledColor').value;
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;
  fetch('/api/led', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({r, g, b})
  });
}

setInterval(refresh, 1000);
refresh();
</script>
</body>
</html>
"""
