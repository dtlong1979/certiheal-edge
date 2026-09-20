"""
CertiHeal-Edge PoC — Vòng 3(b): ĐG3 — dự báo RUL -> DI TRÚ CHỦ ĐỘNG.
Trực giác: lỗi tương quan (một vùng suy thoái) gây BURST lỗi ĐỒNG THỜI -> tranh chấp tuyến
đỉnh-rời -> mất nhiều vai-trò (đúng chế độ khó ta đo ở vòng 1). Nếu dự báo RUL đủ tốt,
ta DI TRÚ TRƯỚC (tuần tự, không tranh chấp) -> biến bài toán khó thành dễ.
Kiểm: preserved-fraction proactive vs reactive theo NHIỄU DỰ BÁO sigma (có điểm hoà vốn?).
"""
import numpy as np, networkx as nx, json, os, time
import poc
OUT=os.path.dirname(os.path.abspath(__file__)); rng=np.random.default_rng(321)

def reactive(G,S,C):
    """Chờ tới lúc cả cụm hỏng ĐỒNG THỜI rồi khôi phục đỉnh-rời tới spare."""
    rec=poc.optimum_disjoint(G,set(C),set(S))
    return min(rec,len(C))/len(C)

def proactive(G,S,C,sigma,tau):
    """Dự báo RUL nhiễu; node bị gắn cờ 'sắp hỏng' -> di trú TRƯỚC (tuần tự, mỗi vai-trò 1 spare rảnh).
    Cụm chưa kịp gắn cờ -> hỏng đồng thời -> khôi phục đỉnh-rời tới spare CÒN LẠI."""
    flagged=[]
    for v in G.nodes():
        if v in S: continue
        true_ttf = 1.0 if v in C else 5.0            # cụm C sắp hỏng; nút khác còn lâu
        pred = true_ttf + rng.normal(0,sigma)        # dự báo nhiễu
        if pred < tau: flagged.append((pred,v))
    flagged.sort()                                   # xử lý nút nguy cấp (RUL thấp) trước
    used_spare=set(); premig=set()
    for _,v in flagged:                              # di trú CHỦ ĐỘNG tuần tự (không tranh chấp)
        avail=[s for s in S if s not in used_spare]
        best=next((s for s in avail if nx.has_path(G,v,s)), None)
        if best: used_spare.add(best); premig.add(v)
    burst=[v for v in C if v not in premig]          # phần cụm chưa cứu kịp -> hỏng đồng thời
    remain=set(s for s in S if s not in used_spare)  # spare đã bị (kể cả false-positive) chiếm bớt
    rec=poc.optimum_disjoint(G,set(burst),remain) if (burst and remain) else 0
    preserved=len([v for v in C if v in premig])+min(rec,len(burst))
    return preserved/len(C)

def main():
    t0=time.time(); GX=GY=8; m=10; K=6; TAU=2.0; RUNS=250
    G=poc.build_grid(GX,GY); S=poc.place_spares(G,m)
    sigmas=[0.0,0.25,0.5,0.75,1.0,1.5,2.0,3.0]
    res={"sigma":sigmas,"reactive":[],"proactive":[]}
    for sg in sigmas:
        pr=[]; re=[]
        for _ in range(RUNS):
            C=poc.sample_failures(G,S,K,clustered=True)   # cụm lỗi tương quan không gian
            re.append(reactive(G,S,C))
            pr.append(proactive(G,S,C,sg,TAU))
        res["reactive"].append(round(float(np.mean(re)),3))
        res["proactive"].append(round(float(np.mean(pr)),3))
    res["params"]={"grid":f"{GX}x{GY}","spares":m,"cluster_K":K,"tau":TAU,"runs":RUNS}
    res["runtime_sec"]=round(time.time()-t0,1)
    json.dump(res,open(os.path.join(OUT,"results_proactive.json"),"w",encoding="utf-8"),
              ensure_ascii=False,indent=2)

    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(7.2,4.8))
    ax.plot(sigmas,res["proactive"],"g-o",label="Chu dong (du bao RUL -> di tru truoc)")
    ax.plot(sigmas,res["reactive"],"r--s",label="Phan ung (cho hong roi khoi phuc)")
    ax.set_xlabel("Nhieu du bao sigma (0 = du bao hoan hao)")
    ax.set_ylabel(f"Ty le vai-tro BAO TOAN (cum K={K})")
    ax.set_ylim(0,1.02); ax.grid(alpha=.3)
    ax.set_title(f"DG3: di tru chu dong theo RUL vs phan ung (8x8, {m} spares)")
    ax.legend(fontsize=9); fig.tight_layout()
    fig.savefig(os.path.join(OUT,"fig5_proactive.png"),dpi=130)

    print(json.dumps({k:res[k] for k in("sigma","reactive","proactive","runtime_sec")},
                     ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
