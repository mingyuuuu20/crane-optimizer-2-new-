const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, BorderStyle, WidthType, ShadingType, ImageRun,
  SectionType, Footnote, FootnoteReferenceRun
} = require('docx');

// ---- 폰트 매핑 (HWP 양식 → 가용 폰트) ----
const HANGUL = "Batang";       // 휴먼명조 ≈ 바탕(명조계열). 없으면 시스템 명조로 대체됨
const HANGUL_G = "Malgun Gothic"; // 맑은고딕
const ENG = "Times New Roman";

const RES = "/home/claude/tower_crane_all/2_validation_figures/";

// helper: 본문 단락 (한글 휴먼명조 9pt = size 18, 행간 150%)
function body(text) {
  return new Paragraph({
    spacing: { line: 360, lineRule: "auto" }, // 150%
    alignment: AlignmentType.JUSTIFIED,
    children: [new TextRun({ text, font: HANGUL, size: 18 })],
  });
}
// 장 제목 (맑은고딕 9pt 진하게)
function chap(text) {
  return new Paragraph({
    spacing: { before: 200, after: 80, line: 360, lineRule: "auto" },
    children: [new TextRun({ text, font: HANGUL_G, size: 18, bold: true })],
  });
}
// 절 제목 (휴먼명조 9pt)
function sect(text) {
  return new Paragraph({
    spacing: { before: 120, after: 60, line: 360, lineRule: "auto" },
    children: [new TextRun({ text, font: HANGUL, size: 18, bold: true })],
  });
}
// 표 제목 (맑은고딕 8pt)
function tcap(text) {
  return new Paragraph({
    spacing: { before: 120, after: 40 },
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text, font: HANGUL_G, size: 16, bold: true })],
  });
}
// 표 각주 (휴먼명조 8pt)
function tnote(text) {
  return new Paragraph({
    spacing: { after: 80 },
    children: [new TextRun({ text, font: HANGUL, size: 16 })],
  });
}
// 그림 캡션
function fcap(text) {
  return new Paragraph({
    spacing: { before: 60, after: 120 },
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text, font: HANGUL_G, size: 16, bold: true })],
  });
}

// ---- 표 빌더 ----
const bd = { style: BorderStyle.SINGLE, size: 4, color: "666666" };
const borders = { top: bd, bottom: bd, left: bd, right: bd };
function cell(text, w, { head=false, font=HANGUL, size=16, align=AlignmentType.CENTER } = {}) {
  return new TableCell({
    borders, width: { size: w, type: WidthType.DXA },
    shading: head ? { fill: "E8EEF4", type: ShadingType.CLEAR } : undefined,
    margins: { top: 50, bottom: 50, left: 80, right: 80 },
    children: [new Paragraph({ alignment: align,
      children: [new TextRun({ text, font, size, bold: head })] })],
  });
}
function row(cells) { return new TableRow({ children: cells }); }

// 표1: 후보 기종 (2단 안에 들어가므로 폭 좁게 ~ 4400 DXA)
const T1W = [1300, 1100, 700, 700, 700]; // sum 4500
const table1 = new Table({
  width: { size: 4500, type: WidthType.DXA }, columnWidths: T1W,
  rows: [
    row([cell("기종",T1W[0],{head:true}), cell("형식",T1W[1],{head:true}),
         cell("최대\n인양(t)",T1W[2],{head:true}), cell("최대\n반경(m)",T1W[3],{head:true}),
         cell("자립고\n(m)",T1W[4],{head:true})]),
    row([cell("Potain MDT 178",T1W[0]), cell("해머헤드",T1W[1]),
         cell("8.0",T1W[2]), cell("60.0",T1W[3]), cell("67.0",T1W[4])]),
    row([cell("Potain MR 160C",T1W[0]), cell("러핑",T1W[1]),
         cell("10.0",T1W[2]), cell("51.0",T1W[3]), cell("50.0",T1W[4])]),
    row([cell("Liebherr 280 HC-L",T1W[0]), cell("러핑",T1W[1]),
         cell("28.0",T1W[2]), cell("60.0",T1W[3]), cell("59.1",T1W[4])]),
  ],
});

// 표2: 9개 제약
const T2W = [600, 1400, 2500]; // sum 4500
const c2rows = [
  ["G1","인양능력","모든 양중점에서 능력 ≥ 요구"],
  ["G2","인접건물 이격","선회면-건물 ≥ 0.6m (KOSHA)"],
  ["G3","본체 침범","인접건물 footprint 침범 금지"],
  ["G4","풍하중 모멘트","전도모멘트 ≤ 허용"],
  ["G5","도달거리","양중점 사각지대 없음"],
  ["G6","후크 높이","마스트 ≥ 건물높이+여유"],
  ["G7","설치 영역","내부/외부설치 자동 판별"],
  ["G8","벽체정착","Wall-tie 가능거리 이내"],
  ["G9","공중 침범","선회면 ⊆ 허용영역(±15%)"],
];
const table2 = new Table({
  width: { size: 4500, type: WidthType.DXA }, columnWidths: T2W,
  rows: [ row([cell("번호",T2W[0],{head:true}), cell("제약",T2W[1],{head:true}),
               cell("내용",T2W[2],{head:true,align:AlignmentType.LEFT})]),
    ...c2rows.map(r=>row([cell(r[0],T2W[0]), cell(r[1],T2W[1]),
                          cell(r[2],T2W[2],{align:AlignmentType.LEFT})])) ],
});

// 표3: 검증 2현장
const T3W = [1100, 700, 1100, 900, 700]; // sum 4500
const table3 = new Table({
  width: { size: 4500, type: WidthType.DXA }, columnWidths: T3W,
  rows: [
    row([cell("현장",T3W[0],{head:true}), cell("대지(㎡)",T3W[1],{head:true}),
         cell("설치방식",T3W[2],{head:true}), cell("추천vs\n실제(m)",T3W[3],{head:true}),
         cell("비고",T3W[4],{head:true})]),
    row([cell("신사동 19-147",T3W[0]), cell("1,140",T3W[1]),
         cell("내부설치(코어)",T3W[2]), cell("1.6",T3W[3]), cell("정량+재현성",T3W[4])]),
    row([cell("방배동 2252",T3W[0]), cell("256",T3W[1]),
         cell("외부+월브레싱",T3W[2]), cell("적용범위규명",T3W[3]), cell("한계규명",T3W[4])]),
  ],
});

// 그림 (2단 폭에 맞게 축소)
const img1 = new Paragraph({
  alignment: AlignmentType.CENTER,
  children: [new ImageRun({ type:"png", data: fs.readFileSync(RES+"sinsa_validation_final.png"),
    transformation: { width: 360, height: 168 },
    altText:{title:"신사동검증",description:"sinsa validation",name:"fig1"} })],
});
const img2 = new Paragraph({
  alignment: AlignmentType.CENTER,
  children: [new ImageRun({ type:"png", data: fs.readFileSync(RES+"bangbae_validation_final.png"),
    transformation: { width: 360, height: 168 },
    altText:{title:"방배동검증",description:"bangbae validation",name:"fig2"} })],
});

// ===== 문서 구성 =====
// 섹션1: 제목/저자/초록 (1단 전폭), 섹션2: 본문 (2단)
const doc = new Document({
  styles: { default: { document: { run: { font: HANGUL, size: 18 } } } },
  footnotes: { 1: { children: [ new Paragraph({ children:[
    new TextRun({ text:"경상국립대학교 건축시스템공학과 학부생", font: HANGUL, size: 16 })]})]} },
  sections: [
    // ---- 섹션 1: 머리부 (1단) ----
    {
      properties: { page: { size: { width:12240, height:15840 },
        margin: { top:1080, right:1080, bottom:1080, left:1080 } } },
      children: [
        new Paragraph({ shading:{fill:"595959",type:ShadingType.CLEAR},
          spacing:{after:160},
          children:[new TextRun({text:"2025년 추계학술발표대회 : 대학생부문",
            font:HANGUL_G, size:18, bold:true, color:"FFFFFF"})]}),
        new Paragraph({ alignment:AlignmentType.CENTER, spacing:{before:120,line:360,lineRule:"auto"},
          children:[new TextRun({text:"도심지 협소대지 타워크레인 배치 다목적 최적화",
            font:HANGUL, size:26})]}),
        new Paragraph({ alignment:AlignmentType.CENTER, spacing:{after:120,line:360,lineRule:"auto"},
          children:[new TextRun({text:"- 실제 시공사례 기반 검증 -", font:HANGUL, size:26})]}),
        new Paragraph({ alignment:AlignmentType.CENTER, spacing:{line:360,lineRule:"auto"},
          children:[new TextRun({text:"Multi-Objective Optimization of Tower Crane Layout on Constrained Urban Sites",
            font:ENG, size:26})]}),
        new Paragraph({ alignment:AlignmentType.CENTER, spacing:{after:160,line:360,lineRule:"auto"},
          children:[new TextRun({text:"- Validation with Real-World Construction Cases -",
            font:ENG, size:22})]}),
        new Paragraph({ alignment:AlignmentType.CENTER, spacing:{line:360,lineRule:"auto"},
          children:[
            new TextRun({text:"○이 민 규", font:HANGUL_G, size:20}),
            new FootnoteReferenceRun(1)]}),
        new Paragraph({ alignment:AlignmentType.CENTER, spacing:{after:160,line:360,lineRule:"auto"},
          children:[new TextRun({text:"Lee, Min-Gyu", font:ENG, size:20})]}),
        // Abstract
        new Paragraph({ alignment:AlignmentType.CENTER, spacing:{before:80,after:40},
          children:[new TextRun({text:"Abstract", font:HANGUL_G, size:18, bold:true})]}),
        new Paragraph({ alignment:AlignmentType.JUSTIFIED, spacing:{line:360,lineRule:"auto"},
          indent:{left:400,right:400},
          children:[new TextRun({ font:ENG, size:16, text:
            "This study proposes a multi-objective optimization framework for tower crane placement on constrained urban sites, where third-party safety risk and lifting efficiency conflict. An NSGA-II algorithm with nine engineering constraints minimizes a third-party safety risk index (F1) and lifting cycle time (F2). Validated against real construction cases in Seoul, the framework reproduced the as-built crane position within 1.6 m on average over repeated runs for a 1,140 m² site, and identified the model's validity envelope through a 256 m² extreme case where wall-tied external mounting falls outside the current modelling assumptions."})]}),
        new Paragraph({ spacing:{before:120,line:360,lineRule:"auto"},
          children:[
            new TextRun({text:"키워드 : ", font:HANGUL_G, size:16, bold:true}),
            new TextRun({text:"타워크레인 배치, 다목적 최적화, NSGA-II, 협소대지, 시공안전", font:HANGUL, size:16})]}),
        new Paragraph({ spacing:{after:80,line:360,lineRule:"auto"},
          children:[
            new TextRun({text:"Keywords : ", font:ENG, size:16, bold:true}),
            new TextRun({text:"Tower Crane Layout, Multi-Objective Optimization, NSGA-II, Constrained Site, Construction Safety", font:ENG, size:16})]}),
      ],
    },
    // ---- 섹션 2: 본문 (2단) ----
    {
      properties: {
        type: SectionType.CONTINUOUS,
        page: { margin: { top:1080, right:1080, bottom:1080, left:1080 } },
        column: { count: 2, space: 480, equalWidth: true, separate: false },
      },
      children: [
        chap("1. 서론"),
        sect("1.1 연구의 배경 및 목적"),
        body("도심지 건축공사에서 타워크레인은 핵심 양중장비이나, 그 배치는 대부분 현장 소장의 경험적 판단에 의존한다. 특히 대지가 협소하고 인접 건물·도로가 밀집한 도심지에서는 크레인의 작업반경이 제3자(보행자·인접 거주자·통행 차량)의 안전을 위협할 수 있으며, 동시에 양중 동선이 길어져 시공 효율이 저하된다. 이 두 요구는 서로 상충한다. 안전을 위해 크레인을 인접 구조물에서 멀리 두면 양중 사이클이 길어지고, 효율을 위해 작업 동선을 짧게 하면 제3자 위험이 증가한다."),
        body("본 연구의 목적은 이러한 상충 관계를 정량적으로 다루는 다목적 최적화 체계를 제안하고, 이를 실제 시공사례로 검증하는 데 있다. 구체적으로 (1) 제3자 안전 위험과 양중 사이클 타임을 두 목적함수로 정식화하고, (2) 9개의 공학적 제약을 적용한 NSGA-II 알고리즘으로 파레토 최적해 집합을 도출하며, (3) 도출된 추천 배치를 서울시 실제 현장의 실측 크레인 위치와 비교하고, 반복 실행에 대한 재현성을 함께 평가하여 체계의 타당성과 적용범위를 규명한다."),
        sect("1.2 선행연구 및 차별성"),
        body("기존 타워크레인 배치 연구는 단일 목적(양중 비용 또는 이동거리)의 최소화에 집중하거나, 안전을 정성적 점검표로만 다루어 왔다. 또한 대다수가 가상의 부지를 대상으로 하여 실제 시공 판단과의 정합성을 검증하지 못했다. 본 연구는 (1) 안전과 효율을 동등한 목적함수로 두어 파레토 트레이드오프를 명시적으로 제시하고, (2) 인양능력·이격·공중침범 등 9개 제약을 정량 모델로 구현하며, (3) 실제 시공된 현장의 크레인 위치와 직접 비교하고 반복 실행의 재현성을 정량적으로 평가한다."),
        body("특히 도심지 협소대지는 인접 구조물과의 이격이 부족하고 가용 설치공간이 제한되어, 크레인 배치 결정이 안전과 효율에 미치는 영향이 일반 현장보다 훨씬 크다. 이러한 조건에서 경험적 판단에만 의존하면 결과의 재현성과 객관성을 담보하기 어렵다. 본 연구가 제안하는 정량적 체계는 동일 입력에 대해 일관된 추천을 제공함으로써, 설계 초기 단계의 의사결정을 보조하고 그 근거를 명시적으로 남길 수 있다."),

        chap("2. 최적화 모델"),
        sect("2.1 결정변수"),
        body("크레인 배치 1기에 대해 5개의 결정변수를 정의한다: 크레인 기초의 평면 좌표 (Cx, Cy), 크레인 기종 선택 변수(3개 후보), 지브 길이, 마스트 높이. 기종 후보는 해머헤드형 1종(대조군)과 협소대지에 적합한 러핑형 2종으로 구성한다(표 1)."),
        tcap("표 1. 타워크레인 후보 기종"),
        table1,
        tnote("주) 제원 출처: 각 제조사 공식 카탈로그(Manitowoc, Liebherr)."),
        sect("2.2 목적함수"),
        body("제3자 안전 위험지수 F1은 위험성평가의 표준 구조인 ‘발생가능성 × 결과심각도’(ISO 31000:2018)를 따른다. 크레인 선회면이 덮는 영역을 용도별로 분할하고, 각 영역의 취약성 가중치를 면적에 곱하여 합산한다. 취약성 가중치는 KOSHA KRAS 위험성평가 및 CIRIA C703을 근거로, 크레인 선회면이 덮는 영역을 도로(5.0), 인접 건물(3.0), 자기 부지·공지(0.5)의 4개 구역으로 분류하여 부여한다. 구역 구분은 입력된 도로 폴리곤·인접 건물 footprint 정보를 기반으로 자동 산정된다. F1은 가중 양중빈도에 선회면적과 취약성의 곱을 적용한 형태로, 사람과 통행이 많은 영역을 덮을수록 증가한다."),
        body("양중 사이클 타임 F2는 각 양중점에 대해 권상·선회·트롤리(또는 러핑) 운동에 소요되는 시간을 제조사 카탈로그의 운동 속도 사양으로 계산하고, 가동률을 반영한 실가동 시간으로 환산하여 비교한다. 두 목적함수는 모두 최소화 대상이다."),
        body("두 목적함수는 서로 다른 단위(위험 지수와 시간)를 가지므로, 절대값의 크기보다 상대적 트레이드오프가 의미를 가진다. 따라서 본 연구는 단일 가중합으로 통합하지 않고 파레토 최적해 집합으로 제시하여, 의사결정자가 현장 여건(인접 민원 수준, 공기 압박 등)에 따라 안전과 효율 사이의 절충점을 선택하도록 한다. 이는 다목적 최적화가 단일 목적 최적화 대비 갖는 실무적 장점이다."),
        sect("2.3 제약조건"),
        body("9개의 부등식 제약을 적용한다(표 2). 인양능력·도달거리·후크높이는 크레인의 물리적 작업 가능성을, 이격·본체침범·공중침범은 인접 구조물 및 대지경계에 대한 안전·법적 요건을, 풍하중·벽체정착은 구조 안정성을 보장한다. 특히 G7(설치영역)은 크레인 기초가 신축 건물 내부에 위치하면 내부설치(코어 클라이밍)로, 부지 안이면 외부 독립기초로 자동 판별하여 협소대지에서 흔한 내부설치 방식을 수용한다."),
        tcap("표 2. 9개 공학적 제약조건"),
        table2,
        tnote("주) 0.6m: KOSHA GUIDE C-104-2020. ±15%: 도로법 시행령 제43조 점용 기준."),
        sect("2.4 최적화 알고리즘"),
        body("다목적 진화알고리즘 NSGA-II를 적용한다. 협소대지에서 크레인이 신축 건물의 남측 혹은 북측 어디에 위치하느냐에 따라 해의 성격이 크게 달라지므로, 탐색 공간을 두 분기(건물 내측/외측)로 나누어 각 기종별로 최적화한 뒤 비지배 해를 통합하는 이중분기(dual-branch) 전략을 사용한다. 최종 추천은 정규화된 두 목적함수의 원점 최근접점(knee point)으로 선정한다."),

        chap("3. 실제 시공사례 검증"),
        sect("3.1 검증 방법"),
        body("검증은 ‘동일한 현장 조건을 입력했을 때, 본 체계의 추천 배치가 실제 시공팀이 선택한 크레인 위치를 재현하는가’를 평가한다. 서울시 내 규모와 설치방식이 서로 다른 2개 현장을 선정하였다(표 3). 각 현장의 대지 형상·인접 건물·도로는 건축물대장, 토지이용계획, 위성영상 및 시공사 설계도면으로 구성하였으며, 실제 크레인 위치는 공사 당시 현장사진 또는 설계도면에서 판독하였다."),
        body("정량 지표는 본 체계가 추천한 크레인 기초 위치(knee point)와 실제 시공된 크레인 위치 사이의 평면 거리로 정의한다. NSGA-II는 확률적 알고리즘이므로, 단일 실행 결과의 우연성을 배제하기 위해 서로 다른 난수 시드로 반복 실행하여 추천 위치의 재현성을 함께 평가한다. 이 거리가 양중점 간격 수준으로 반복 재현되면 추천이 실제 판단을 사실상 동일하게 재현한 것으로 본다."),
        tcap("표 3. 검증 대상 2개 현장"),
        table3,
        sect("3.2 사례 1: 신사동 19-147 (정량 검증 및 재현성)"),
        body("신사동 19-147 승윤노블리안(대지 1,140㎡)은 크레인을 신축 건물 코어 내부에 설치한 내부설치 사례로, 북측에 빈 공지(주차장)가 인접한다. 빈 대지 상공으로의 선회를 허용하도록 모델링한 결과, 파레토 약 90개 해가 도출되었으며 knee 추천은 Liebherr 280 HC-L, 지브 20m로서 실제 크레인 위치와 약 1.4m 차이였다(그림 1)."),
        body("추천의 재현성을 확인하기 위해 서로 다른 난수 시드로 반복 실행한 결과, 대부분의 실행에서 추천 위치가 실측 위치 인근의 좁은 영역(평면 좌표 폭 약 3m 이내)으로 일관되게 수렴하였으며, 실측과의 거리는 평균 약 1.6m(편차 약 0.3m)로 안정적이었다. 일부 실행에서는 전역 최적화의 확률적 특성상 국소해로 수렴하는 경우가 드물게 관찰되었으나, 다수 실행의 추천은 실측 위치를 양중점 간격 수준으로 반복 재현하였다. 이는 본 체계의 추천이 단일 실행의 우연이 아니라 재현 가능한 결과임을 뒷받침한다."),
        img1,
        fcap("그림 1. 신사동 사례 검증 (좌: 파레토 front, 우: 추천 vs 실제 배치)"),
        sect("3.3 사례 2: 방배동 2252 (적용범위 규명)"),
        body("방배동 2252(대지 256㎡)는 극협소대지에 무인 러핑 크레인(FT-80L)을 외부설치하고 벽체정착(월브레싱) 2단으로 시공한 사례이다. 크레인 제원은 시공사 설계도면, 시공사 현장기록, 장비 카탈로그의 3중 교차검증으로 확정하였다(작업반경 20m, 지브 20m, 마스트 50m). 본 체계로 최적화한 결과 파레토 해는 모두 내부설치로 도출되었다. 실제 시공에서는 크레인을 대지 외부에 놓고 신축 건물 벽체에 정착시키는 '벽체정착 외부설치(월브레싱)' 공법이 사용되었으나, 본 모델은 독립기초 설치를 가정하므로 이 공법을 표현하지 못한다. 또한 대지 256㎡에서 크레인 선회면이 대지의 약 4.9배에 달해 G9 제약을 위반하며, 외부 독립기초 설치 공간도 부족하여 G7 제약도 만족하지 못한다."),
        body("이는 본 체계의 적용범위(validity envelope)를 드러낸다. 모델은 대지면적 약 1,000㎡ 이상의 협소대지에서 실측을 재현하나, 256㎡급 극협소대지에서 사용되는 ‘벽체정착 외부설치’ 공법은 현재 모델이 표현하지 못한다. 이 한계를 인위적으로 우회하지 않고 명시함이 검증의 신뢰성을 보장한다(그림 2)."),
        img2,
        fcap("그림 2. 방배동 사례 — 추천(내부설치) vs 실제(외부설치) 및 적용범위 규명"),

        chap("4. 고찰"),
        body("두 사례를 종합하면, 본 체계의 재현 정확도는 대지 규모 및 설치방식과 밀접하게 연관된다. 코어 내부설치를 채택한 1,000㎡ 규모의 신사동 사례에서는 추천 배치가 실측 위치를 양중점 간격 이내(평균 약 1.6m)로, 그것도 반복 실행에 걸쳐 안정적으로 재현하였다. 이는 해당 규모대에서 안전·효율의 상충을 두 목적함수로 정식화하고 9개 제약으로 제한한 모델이 실제 시공팀의 경험적 판단과 정합하며, 그 결과가 우연이 아님을 시사한다."),
        body("추천 위치와 실제 위치 사이에 잔존하는 약 1.6m의 차이는 크게 세 가지 요인으로 설명할 수 있다. 첫째, 본 모델은 양중점을 건물 footprint의 균등 격자로 단순화하는 반면, 실제 시공팀은 층별 자재 계획·반입구 위치·가설 동선 등 현장 고유의 세부 정보를 추가로 고려한다. 둘째, 실제 크레인 설치 위치는 기초 공사 가능 여부·지하 매설물·인근 민원 등 현장 조건에 따라 미세 조정되며, 이러한 비정형적 요인은 수리 모델로 표현하기 어렵다. 셋째, NSGA-II의 확률적 특성상 동일 조건에서도 추천 위치가 소폭 변동하며, 반복 실행 기준 편차는 0.3m 수준으로 안정적이나 절대값의 미세한 분산은 불가피하다. 이러한 요인들을 감안하면, 1.6m의 잔존 오차는 모델 구조의 본질적 단순화에서 비롯된 합리적 범위 내의 편차로 해석할 수 있다."),
        body("반면 256㎡급 극협소대지(방배)에서는 슬루 반경이 대지면적을 크게 초과(선회면이 대지의 약 4.9배)하고, 크레인이 신축 건물 벽체에 정착하는 외부설치가 사용되어 모델의 가정과 불일치하였다. 이러한 경계 사례는 모델의 한계를 드러내는 동시에, 적용 가능 범위를 정량적으로 규정한다는 점에서 의의가 있다. 즉 본 체계는 일정 규모 이상의 협소대지에 대해 신뢰성 있는 사전 검토 도구로 활용될 수 있으며, 극협소·특수공법 현장으로의 확장은 후속 과제로 남는다."),

        chap("5. 결론"),
        body("본 연구는 도심지 협소대지의 타워크레인 배치를 제3자 안전과 양중 효율의 상충 문제로 정식화하고, 9개 공학적 제약을 적용한 NSGA-II 다목적 최적화 체계를 제안하였다. 서울시 실제 현장 검증 결과, 1,000㎡ 규모의 협소대지에서 추천 배치가 실측 크레인 위치를 평균 약 1.6m로, 반복 실행에 걸쳐 안정적으로 재현하여 체계의 타당성과 재현성을 입증하였다. 또한 256㎡급 극협소대지 사례를 통해 모델의 적용범위와 한계를 정량적으로 규명하였다."),
        body("향후 연구로는 (1) 벽체정착 외부설치 방식의 제약 모델 추가, (2) 평면 침범이 아닌 3차원 충돌(지브·인양물 높이와 인접 건물 높이) 기반의 공중침범 판정, (3) 러핑 크레인의 가변 작업반경 운용 모델 도입이 필요하다."),

        chap("참고문헌"),
        new Paragraph({ spacing:{line:340,lineRule:"auto"}, children:[new TextRun({text:"1. ISO, ISO 31000:2018 Risk Management Guidelines, 2018", font:ENG, size:18})]}),
        new Paragraph({ spacing:{line:340,lineRule:"auto"}, children:[new TextRun({text:"2. 안전보건공단, KOSHA GUIDE C-104-2020 타워크레인 안전작업 지침, 2020", font:HANGUL, size:16})]}),
        new Paragraph({ spacing:{line:340,lineRule:"auto"}, children:[new TextRun({text:"3. Deb, K. et al., A Fast and Elitist Multiobjective Genetic Algorithm: NSGA-II, IEEE Trans. Evol. Comput., 6(2), 2002, pp.182-197", font:ENG, size:18})]}),
        new Paragraph({ spacing:{line:340,lineRule:"auto"}, children:[new TextRun({text:"4. CIRIA, C703 Crane Stability on Site, 2003", font:ENG, size:18})]}),
      ],
    },
  ],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync("/home/claude/논문_방배동검증_워드.docx", buf);
  console.log("saved docx");
});
