# Pilot Closed-loop 驗證

正式 Pilot 將 Recommendation → Action → Outcome → Learning 串成可追溯閉環。`data/pilot/action_outcomes_template.csv` 目前只有 header，沒有虛構採行、節油或成效列。

先記錄推薦是否被接受、誰接手、何時執行、實際措施及後續行程。Recommendation Adoption Rate = 接受建議數 / 已呈現建議數；Action Completion Rate = 已完成行動數 / 已接受建議數。分母為零或未追蹤時留空。

燃油效率與觀測怠速情境須用任務、車型、路線、載重、時段等可比較條件做 before/after；可行時使用處置組與對照組，並記錄天氣、路況與維修變化。另追蹤調度／管理核對所需時間。差距縮小不自動等於措施造成；需對照組、足夠樣本與情境核對。PTO、真實停靠用途與作業需求到位後，才可能評估怠速是否可改善。
