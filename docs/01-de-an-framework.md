# De an ca nhan: Agent-Based Simulation and Mechanism Design for Transaction Risk Decisioning

## 1. Huong de tai

Ten de tai du kien:

Agent-Based Simulation and Mechanism Design for Transaction Risk Decisioning in Digital Finance

Ten tieng Viet:

Mo phong da tac nhan va thiet ke co che trong ra quyet dinh rui ro giao dich so

Huong de tai nay khong tap trung vao viec xay dung mot mo hinh fraud detection co accuracy cao nhat. Trong tam cua de tai la mo phong va danh gia co che ra quyet dinh rui ro trong moi truong giao dich so, noi cac tac nhan khac nhau co hanh vi, loi ich va phan ung khac nhau.

Thay vi chi hoi "giao dich nay co phai fraud khong", de tai hoi:

- Khi he thong AI dua ra risk score, nen thiet ke co che review nhu the nao?
- Threshold canh bao anh huong the nao den fraud loss, false positive cost va workload cua analyst?
- Neu them AI explanation/report thi co the giam review time va cai thien chat luong quyet dinh khong?
- Chinh sach nao dem lai expected net benefit tot hon trong dieu kien tai nguyen analyst bi gioi han?

## 2. Ly do chon de tai

Trong linh vuc fintech va ngan hang so, he thong phat hien rui ro giao dich thuong dung rule-based system hoac machine learning model de cham diem rui ro. Tuy nhien, risk score chi la mot tin hieu. Quyet dinh nghiep vu cuoi cung con phu thuoc vao analyst, quy trinh review, chi phi sai sot, trai nghiem khach hang va nang luc van hanh cua to chuc.

Neu chi danh gia model bang precision, recall hoac PR-AUC thi chua du de tra loi cau hoi nghiep vu: he thong co that su giup giam ton that, giam thoi gian xu ly va toi uu chi phi khong?

Vi vay, de tai nay tiep can bai toan theo huong co che:

- Fraud actor co the thay doi hanh vi de tranh bi phat hien.
- Khach hang binh thuong co the bi anh huong neu bi review/block nham.
- Analyst co gioi han ve thoi gian va nang luc xu ly.
- Ngan hang/fintech platform can can bang giua fraud loss va customer friction.
- AI agent co the ho tro giai thich, nhung khong duoc thay the quyet dinh cua con nguoi.

Huong nay phu hop voi gop y ve Game Theory, Mechanism Design va Agent-Based Modeling: khong chi mo phong du lieu, ma mo phong tuong tac va phan ung cua cac tac nhan trong mot co che ra quyet dinh.

## 3. Cau hoi nghien cuu

Cau hoi trung tam:

Co che ket hop risk scoring, analyst review va AI explanation co the cai thien hieu qua ra quyet dinh rui ro giao dich so nhu the nao?

Cac cau hoi phu:

1. Khi thay doi risk threshold, fraud loss prevented, false positive cost va analyst workload thay doi ra sao?
2. Co che ML + analyst review co tot hon rule-based only khong?
3. AI explanation/report co the giam review time va ho tro analyst ra quyet dinh on dinh hon khong?
4. Dau la policy co expected net benefit tot nhat trong cac kich ban fraud rate, transaction volume va analyst capacity khac nhau?
5. Khi fraud actor dieu chinh chien luoc, co che hien tai co con ben vung khong?

## 4. Nen tang ly thuyet can viet trong bao cao

### 4.1. Transaction Risk Decisioning

Transaction risk decisioning la qua trinh danh gia va xu ly rui ro cua tung giao dich. Trong thuc te, mot giao dich co the duoc approve, review, step-up authentication, decline hoac block tuy vao score, rule, bang chung va policy noi bo.

Diem quan trong la he thong khong chi du bao nhan fraud/non-fraud. No phai tao ra mot quy trinh quyet dinh co chi phi va loi ich ro rang.

### 4.2. Machine Learning Risk Scoring

ML risk scoring dung du lieu giao dich, hanh vi gan day, merchant, thoi gian, velocity, amount anomaly va cac feature lien quan de uoc luong muc do rui ro. Output thuong la probability hoac risk score.

Han che cua risk score:

- Score khong tu dong bang quyet dinh fraud.
- Score cao co the lam tang false positive neu threshold qua thap.
- Score thap van co the bo sot fraud neu hanh vi gian lan thay doi.
- Model metric ky thuat chua chac quy doi truc tiep thanh loi ich kinh doanh.

### 4.3. Explainable AI va SHAP

Explainable AI giup analyst hieu vi sao mo hinh cham diem rui ro cao. SHAP co the duoc dung de giai thich dong gop cua tung feature vao risk score.

Trong boi canh nay, SHAP khong duoc xem la bang chung ket luan fraud, ma la bang chung ho tro review. Vi du:

- Amount anomaly lam tang risk score.
- Transaction hour la khung gio bat thuong.
- Velocity 1h/24h cho thay tan suat giao dich cao.
- Gap since previous transaction cho thay khoang cach giao dich sat nhau.

### 4.4. Human-in-the-loop Decisioning

Do rui ro phap ly va nghiep vu, AI khong nen tu dong ket luan fraud hoac tu dong block tai khoan. Analyst can giu vai tro ra quyet dinh cuoi cung.

Human-in-the-loop giup:

- Giam rui ro tu dong hoa sai.
- Ghi nhan feedback de cai thien he thong.
- Dam bao cac case nhay cam duoc xac minh boi con nguoi.
- Tao audit trail cho quy trinh ra quyet dinh.

### 4.5. Game Theory

Game Theory nghien cuu tinh huong trong do nhieu tac nhan co loi ich rieng va quyet dinh cua moi tac nhan anh huong den ket qua cua tac nhan khac.

Trong bai toan nay:

- Fraud actor muon toi da hoa loi ich bat hop phap va tranh bi phat hien.
- Ngan hang muon giam fraud loss nhung khong muon tang friction qua muc.
- Analyst muon xu ly dung nhung bi gioi han thoi gian.
- Khach hang binh thuong muon giao dich nhanh, it bi chan nham.

Day khong phai bai toan du bao tinh tai, ma la bai toan tuong tac chien luoc.

### 4.6. Mechanism Design

Mechanism Design co the hieu la thiet ke luat choi de dan dat hanh vi cua cac tac nhan den ket qua mong muon.

Trong transaction risk decisioning, mechanism co the la:

- Risk threshold nao thi approve/review/block.
- Case nao uu tien analyst xu ly truoc.
- Khi nao can step-up authentication.
- Khi nao can AI explanation/report.
- Feedback cua analyst duoc dung de cap nhat policy ra sao.

Muc tieu khong chi la bat duoc nhieu fraud, ma la thiet ke co che can bang giua loss prevention, cost, workload va customer experience.

### 4.7. Agent-Based Modeling

Agent-Based Modeling mo phong he thong bang cach tao cac tac nhan rieng le, moi tac nhan co hanh vi va quy tac ra quyet dinh rieng. Tuong tac giua cac agent tao ra hanh vi tong the cua he thong.

Trong de tai nay, ABM phu hop vi:

- Co nhieu tac nhan voi loi ich khac nhau.
- Fraud behavior co the thay doi theo policy.
- Analyst capacity co gioi han.
- Outcome chi xuat hien sau chuoi tuong tac, khong nam san trong bang du lieu tinh.

## 5. Thiet ke agent trong mo phong

### 5.1. Normal Customer Agent

Dai dien cho khach hang hop le.

Thuoc tinh:

- spending profile
- normal transaction amount distribution
- active hours
- preferred merchant categories
- tolerance to friction

Hanh vi:

- Tao giao dich theo pattern ca nhan.
- Co the bi anh huong neu bi review/block nham.

### 5.2. Fraud Actor Agent

Dai dien cho hanh vi gian lan.

Thuoc tinh:

- attack intensity
- amount strategy
- time strategy
- evasion ability
- adaptation speed

Hanh vi:

- Tao giao dich rui ro cao.
- Co the thay doi amount, timing hoac frequency neu policy qua de bi phat hien.

### 5.3. Risk Scoring System Agent

Dai dien cho model/rule system.

Input:

- transaction features
- customer recent behavior
- velocity features
- merchant/context features

Output:

- risk score
- risk level
- explanation features

### 5.4. Analyst Agent

Dai dien cho nguoi review case.

Thuoc tinh:

- daily capacity
- review accuracy
- review time
- effect of AI explanation on review speed

Hanh vi:

- Nhan case theo priority.
- Ra quyet dinh approve/reject/escalate theo bang chung.
- Tao feedback sau review.

### 5.5. Platform/Bank Agent

Dai dien cho to chuc van hanh he thong.

Muc tieu:

- Giam fraud loss.
- Giam false positive cost.
- Giam customer friction.
- Toi uu analyst workload.
- Toi da hoa expected net benefit.

### 5.6. Policy Maker Agent

Dai dien cho co che dieu chinh policy.

Hanh vi:

- Chon threshold.
- Chon rule review.
- Chon khi nao dung AI explanation.
- Dieu chinh policy dua tren KPI.

## 6. Policy can so sanh

Co the mo phong 4 policy:

1. Rule-based only
   - Chi dung rule don gian nhu amount threshold, velocity threshold.

2. ML score threshold
   - Dung risk score de quyet dinh approve/review/block.

3. ML + analyst review
   - Risk score dung de uu tien case, analyst ra quyet dinh cuoi.

4. ML + analyst review + AI explanation
   - Them AI explanation/report de giam review time va tang do ro rang cua bang chung.

## 7. KPI danh gia

### 7.1. Model metrics

Dung de danh gia risk scoring:

- Precision
- Recall
- F1-score
- PR-AUC
- ROC-AUC
- False positive rate
- False negative rate

### 7.2. Operational metrics

Dung de danh gia van hanh:

- Analyst workload
- Average review time
- Case backlog
- Escalation rate
- Review throughput
- Cost per reviewed case

### 7.3. Business metrics

Dung de danh gia hieu qua kinh doanh:

- Fraud loss prevented
- Fraud loss missed
- False positive cost
- Customer friction cost
- Expected net benefit

Cong thuc goi y:

Expected Net Benefit = Fraud Loss Prevented - False Positive Cost - Analyst Review Cost - AI Usage Cost - Customer Friction Cost

### 7.4. AI Agent metrics

Dung de danh gia LLM agent:

- Groundedness: cau tra loi co dua tren evidence khong
- PII safety: co tu choi khi hoi thong tin nhay cam khong
- Scope control: co tu choi cau hoi ngoai pham vi khong
- Naturalness: cau tra loi co tu nhien, khong JSON cung khong
- Latency
- Token cost

## 8. Data simulation framework

Du lieu khong nen duoc mo phong ngau nhien hoan toan. Nen mo phong theo co che:

1. Sinh customer profiles.
2. Sinh normal transaction behavior.
3. Sinh fraud actor behavior.
4. Risk system cham diem.
5. Policy quyet dinh approve/review/block.
6. Analyst review case neu can.
7. Ghi nhan outcome.
8. Tinh KPI.

Bang du lieu du kien:

- customers
- transactions
- risk_scores
- cases
- analyst_decisions
- policy_runs
- simulation_metrics
- agent_messages/report_logs neu co AI agent

## 9. San pham demo du kien

San pham ca nhan co the la mot dashboard mo phong:

- Simulation setup: chon fraud rate, volume, threshold, analyst capacity.
- Dashboard: tong quan fraud loss, false positive cost, workload.
- Case queue: danh sach case can review.
- Case detail: risk evidence va explanation.
- Report: AI tom tat case va goi y review step.
- Policy comparison: so sanh expected net benefit giua cac policy.

## 10. Lo trinh truoc mat

Buoc 1: Hoan thien de cuong va nen tang ly thuyet.

Buoc 2: Thiet ke simulation schema va agent rules.

Buoc 3: Tao notebook/data generator de sinh du lieu simulation nho.

Buoc 4: Tinh KPI cho cac policy co ban.

Buoc 5: Rebrand code framework cu thanh san pham ca nhan moi.

Buoc 6: Tich hop AI agent/report de giai thich policy va case.

## 11. Ket luan dinh huong

De tai nay giu duoc tinh FinTech va AI cua du an ban dau, nhung chuyen trong tam tu xay dung fraud detection product sang nghien cuu va mo phong co che ra quyet dinh rui ro. Diem khac biet la he thong khong chi tra loi "model cham diem dung khong", ma danh gia "co che ra quyet dinh nao toi uu hon khi co nhieu tac nhan, chi phi va phan ung trong he thong".
