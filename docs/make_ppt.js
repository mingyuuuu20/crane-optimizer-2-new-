const pptxgen = require("pptxgenjs");
const p = new pptxgen();
p.defineLayout({ name: "W", width: 13.333, height: 7.5 });
p.layout = "W";

const NAVY="1F3A5F", NAVY2="2E5A8A", GOLD="C8A24B", LGOLD="F5EBD6",
      INK="1A1A1A", GREY="6B7785", LIGHT="F4F6F8", WHITE="FFFFFF";
const HF="Georgia", BF="Calibri";
const A = (f)=>`/home/claude/ppt_assets/${f}`;

// ---------- helpers ----------
function titleBar(s, t, kicker){
  s.addText(kicker, {x:0.6,y:0.45,w:11,h:0.3,fontFace:BF,fontSize:12,color:GOLD,bold:true,charSpacing:2});
  s.addText(t, {x:0.6,y:0.72,w:12.1,h:0.8,fontFace:HF,fontSize:28,color:NAVY,bold:true});
}

// ========== Slide 1: 표지 (dark) ==========
let s = p.addSlide(); s.background={color:NAVY};
s.addText("2025 추계학술발표대회 · 대학생부문", {x:0.8,y:1.6,w:11,h:0.4,fontFace:BF,fontSize:14,color:GOLD,bold:true,charSpacing:2});
s.addText("도심지 협소대지\n타워크레인 배치 다목적 최적화", {x:0.8,y:2.15,w:11.7,h:1.9,fontFace:HF,fontSize:40,color:WHITE,bold:true,lineSpacing:46});
s.addText("- 실제 시공사례 기반 검증 -", {x:0.8,y:4.15,w:11,h:0.5,fontFace:HF,fontSize:20,color:"CADCFC",italic:true});
s.addShape(p.ShapeType.line,{x:0.85,y:5.5,w:3.5,h:0,line:{color:GOLD,width:2}});
s.addText("경상국립대학교 건축시스템공학과   이민규", {x:0.8,y:5.7,w:11,h:0.4,fontFace:BF,fontSize:16,color:WHITE});
s.addText("NSGA-II · 9개 공학적 제약 · 실제 시공사례 검증 및 재현성", {x:0.8,y:6.15,w:11,h:0.35,fontFace:BF,fontSize:12,color:"8FA3BF"});

// ========== Slide 2: 배경·문제 ==========
s = p.addSlide(); s.background={color:WHITE};
titleBar(s,"왜 필요한가 — 두 요구의 충돌","연구 배경");
// 좌: 설명
s.addText([
  {text:"도심지 타워크레인 배치는 대부분 ",options:{}},
  {text:"현장소장의 경험",options:{bold:true,color:NAVY}},
  {text:"에 의존한다.",options:{}},
],{x:0.6,y:1.9,w:6.0,h:0.9,fontFace:BF,fontSize:16,color:INK,lineSpacing:24});
// 두 카드 (상충)
s.addShape(p.ShapeType.roundRect,{x:0.6,y:3.0,w:5.9,h:1.6,rectRadius:0.1,fill:{color:LGOLD},line:{color:GOLD,width:1.5}});
s.addText("① 제3자 안전",{x:0.8,y:3.15,w:5,h:0.4,fontFace:HF,fontSize:18,bold:true,color:NAVY});
s.addText("크레인 작업반경이 보행자·인접 거주자·통행 차량을 위협",{x:0.8,y:3.6,w:5.5,h:0.9,fontFace:BF,fontSize:14,color:INK,lineSpacing:20});
s.addShape(p.ShapeType.roundRect,{x:0.6,y:4.8,w:5.9,h:1.6,rectRadius:0.1,fill:{color:"E8EEF4"},line:{color:NAVY2,width:1.5}});
s.addText("② 양중 효율",{x:0.8,y:4.95,w:5,h:0.4,fontFace:HF,fontSize:18,bold:true,color:NAVY2});
s.addText("안전하게 멀리 두면 양중 동선이 길어져 시공 효율 저하",{x:0.8,y:5.4,w:5.5,h:0.9,fontFace:BF,fontSize:14,color:INK,lineSpacing:20});
// 우: 충돌 도식 + 목표
s.addShape(p.ShapeType.roundRect,{x:7.0,y:1.95,w:5.7,h:2.4,rectRadius:0.1,fill:{color:NAVY}});
s.addText("상충 관계 (Trade-off)",{x:7.2,y:2.1,w:5.3,h:0.4,fontFace:HF,fontSize:17,bold:true,color:GOLD});
s.addText([
  {text:"안전 ↑  →  효율 ↓\n",options:{color:WHITE}},
  {text:"효율 ↑  →  안전 ↓",options:{color:WHITE}},
],{x:7.2,y:2.7,w:5.3,h:1.0,fontFace:BF,fontSize:20,bold:true,align:"center",lineSpacing:34});
s.addText("→ 한쪽만 좋게 할 수 없다.\n   둘을 동시에 최적화해야 한다.",{x:7.2,y:3.65,w:5.3,h:0.6,fontFace:BF,fontSize:13,color:"CADCFC",italic:true,align:"center",lineSpacing:18});
s.addShape(p.ShapeType.roundRect,{x:7.0,y:4.6,w:5.7,h:1.8,rectRadius:0.1,fill:{color:LIGHT},line:{color:GOLD,width:1.5}});
s.addText("본 연구의 목표",{x:7.2,y:4.75,w:5.3,h:0.4,fontFace:HF,fontSize:16,bold:true,color:NAVY});
s.addText([
  {text:"① 안전·효율을 두 목적함수로 정식화\n"},
  {text:"② 9개 공학적 제약 + NSGA-II 최적화\n"},
  {text:"③ 실제 사례 검증 + 재현성 확인"},
],{x:7.2,y:5.2,w:5.3,h:1.1,fontFace:BF,fontSize:14,color:INK,lineSpacing:22});

// ========== Slide 3: 방법 (플로우) ==========
s = p.addSlide(); s.background={color:WHITE};
titleBar(s,"어떻게 작동하는가 — 입력·처리·출력","방법론");
s.addImage({path:A("flow.png"),x:1.07,y:2.1,w:11.2,h:5.56});
// flow.png는 2.01 비율 → w12.33 h6.13 너무 큼. 조정
// (아래 재배치)

// ========== Slide 4: 시스템 (앱) ==========
s = p.addSlide(); s.background={color:WHITE};
titleBar(s,"구현한 도구 — 인터랙티브 최적화 시스템","시스템");
s.addImage({path:A("app.png"),x:1.2,y:1.75,w:10.9,h:10.9/1.65});
s.addText("Python · pymoo · Streamlit  |  부지 선택 → 최적화 실행 → 9개 제약 검증 → 결과 시각화",
  {x:0.6,y:6.95,w:12.1,h:0.35,fontFace:BF,fontSize:12,color:GREY,italic:true,align:"center"});

// ========== Slide 5: 검증 1·2 (정량) ==========
s = p.addSlide(); s.background={color:WHITE};
titleBar(s,"검증 — 추천이 실제 시공을 재현하는가","실제 사례 검증 (1)");
s.addImage({path:A("sinsa.png"),x:0.5,y:1.75,w:8.3,h:8.3/2.29});
// 우측 수치 카드
s.addShape(p.ShapeType.roundRect,{x:9.1,y:1.8,w:3.6,h:2.3,rectRadius:0.1,fill:{color:NAVY}});
s.addText("신사동 19-147",{x:9.3,y:1.95,w:3.2,h:0.4,fontFace:HF,fontSize:16,bold:true,color:GOLD});
s.addText([
  {text:"대지 1,140㎡ · 내부설치\n\n",options:{color:"CADCFC",fontSize:13}},
  {text:"1.6m",options:{color:WHITE,fontSize:44,bold:true}},
  {text:"\n추천 vs 실제 (평균)",options:{color:"CADCFC",fontSize:12}},
],{x:9.3,y:2.4,w:3.2,h:1.6,fontFace:BF,align:"center",lineSpacing:18});
s.addShape(p.ShapeType.roundRect,{x:9.1,y:4.3,w:3.6,h:2.0,rectRadius:0.1,fill:{color:LGOLD},line:{color:GOLD,width:1.5}});
s.addText("재현성 검증",{x:9.3,y:4.45,w:3.2,h:0.4,fontFace:HF,fontSize:15,bold:true,color:NAVY});
s.addText([
  {text:"반복 실행(다중 시드)\n\n",options:{color:GREY,fontSize:12}},
  {text:"편차 0.3m",options:{color:NAVY,fontSize:30,bold:true}},
  {text:"\n좁은 영역에 안정 수렴",options:{color:GREY,fontSize:11}},
],{x:9.3,y:4.85,w:3.2,h:1.4,fontFace:BF,align:"center",lineSpacing:16});
s.addText("→ 추천 배치가 실제 시공 판단을 양중점 수준(평균 1.6m)으로, 반복 실행에 걸쳐 안정적으로 재현",
  {x:0.6,y:6.95,w:12.1,h:0.35,fontFace:BF,fontSize:13,color:NAVY,bold:true,align:"center"});

// ========== Slide 6: 검증 3 (한계) ==========
s = p.addSlide(); s.background={color:WHITE};
titleBar(s,"적용범위 규명 — 정직한 한계","실제 사례 검증 (2)");
s.addImage({path:A("bangbae.png"),x:0.5,y:1.8,w:7.6,h:7.6/2.15});
s.addShape(p.ShapeType.roundRect,{x:8.4,y:1.8,w:4.3,h:4.7,rectRadius:0.1,fill:{color:LIGHT},line:{color:NAVY2,width:1.5}});
s.addText("방배동 2252",{x:8.6,y:1.95,w:3.9,h:0.4,fontFace:HF,fontSize:17,bold:true,color:NAVY});
s.addText([
  {text:"대지 256㎡ (극협소) · 외부설치+월브레싱\n",options:{color:GREY,fontSize:12,bold:true}},
  {text:"크레인: FT-80L (무인 러핑)\n\n",options:{color:INK,fontSize:12}},
  {text:"추천 = 내부설치 / 실제 = 외부설치\n",options:{color:NAVY,fontSize:13,bold:true}},
  {text:"→ 두 공법 불일치\n\n",options:{color:INK,fontSize:12}},
  {text:"모델 적용범위 밖:\n",options:{color:GOLD,fontSize:13,bold:true}},
  {text:"1,000㎡↑ 협소대지는 재현하나, 256㎡급 + 벽체정착 외부설치는 미지원",options:{color:INK,fontSize:12}},
],{x:8.6,y:2.45,w:3.9,h:3.9,fontFace:BF,lineSpacing:17});
s.addText("FT-80L 제원은 시공사 도면·현장기록·카탈로그 3중 교차검증 (반경 20m, 마스트 50m). 한계를 우회하지 않고 명시.",
  {x:0.6,y:6.95,w:12.1,h:0.4,fontFace:BF,fontSize:12,color:GREY,italic:true,align:"center"});

// ========== Slide 7: 결론 (dark) ==========
s = p.addSlide(); s.background={color:NAVY};
s.addText("결론",{x:0.8,y:0.7,w:11,h:0.6,fontFace:HF,fontSize:30,bold:true,color:GOLD});
// 3 stat
const stats=[["1.6m","추천 vs 실제 (평균)","E8EEF4"],["0.3m","재현성 편차","E8EEF4"],["9","개 공학적 제약","E8EEF4"]];
stats.forEach((st,i)=>{
  const x=0.8+i*4.05;
  s.addShape(p.ShapeType.roundRect,{x:x,y:1.7,w:3.7,h:1.7,rectRadius:0.1,fill:{color:"2A4A6E"}});
  s.addText(st[0],{x:x,y:1.85,w:3.7,h:0.8,fontFace:HF,fontSize:34,bold:true,color:GOLD,align:"center"});
  s.addText(st[1],{x:x,y:2.7,w:3.7,h:0.5,fontFace:BF,fontSize:13,color:"CADCFC",align:"center"});
});
s.addText("핵심 성과",{x:0.8,y:3.8,w:11,h:0.4,fontFace:HF,fontSize:18,bold:true,color:WHITE});
s.addText([
  {text:"• 안전·효율 상충을 다목적 최적화로 정식화하고 NSGA-II로 파레토 해 도출\n"},
  {text:"• 1,000㎡ 규모 협소대지에서 실측 위치를 평균 1.6m로, 반복 실행에 걸쳐 안정적으로 재현\n"},
  {text:"• 극협소대지 사례로 모델 적용범위와 한계를 정직하게 규명"},
],{x:0.85,y:4.25,w:11.6,h:1.3,fontFace:BF,fontSize:15,color:"E8EEF4",lineSpacing:26});
s.addText("향후: ① 벽체정착 외부설치 모델 ② 3차원 충돌 기반 공중침범 ③ 러핑 가변반경 운용",
  {x:0.85,y:5.75,w:11.6,h:0.5,fontFace:BF,fontSize:13,color:GOLD,italic:true});
s.addText("경상국립대학교 건축시스템공학과 · 이민규",{x:0.85,y:6.7,w:11.6,h:0.4,fontFace:BF,fontSize:12,color:"8FA3BF"});

p.writeFile({ fileName: "/home/claude/발표자료_타워크레인.pptx" }).then(f=>console.log("saved",f));
