# -*- coding: utf-8 -*-
#######
# LabelCheck_ver2.py
# テンプレート画像を表示するところまで。
# キャプチャ画像を表示するところまで。
# 合格基準値をCSVから読み込んでテンプレート画像の下に表示するところまで。2020/9/22
# loadボタンで読み込んだ画像１をテンプレートとして、マッチングまでOK　2020/9/23

''' カメラで被検査物をキャプチャし、２つの比較画像（テンプレート）と照合(テンプレートマッチング）。
    適合率、ロケーション(X,Y)で合否判定する。
    比較画像とそれの正位置（合格位置）、適合率のしきい値はマスタDBに登録、参照する。
    GUI上のテキストボックスでID（PartNo)を入力しDBより取得する。
    (とりあえずはtxtboxに部品コードを入力後、loadボタンを押すと、テンプレート画像とそれの位置、しきい値情報をCSVから取得し表示する)
    GUIはtkinterで作成。GUI上はrootにframe1,2,3を作る。
    frame1にキャプチャ映像と判定結果画像（検出画像を四角で囲う。Gは青、NGは赤）、判定結果（文字)を表示する。
    アプリ起動するとキャプチャ画像（動画）を表示し、'check'ボタンで判定結果画像（静止画）を表示する。'clear'で動画に戻る
    frame2,3にテンプレート画像と正位置と適合率の合格しきい値を表示。
    "check"ボタンで照合実行
    2020/10/5 判定結果で四角を青、赤にするところまで。
    2020/10/9 clearボタンで画像をカメラ動画に戻し、x,y,適合率の結果表示を消す。ところまで。
    2020/10/18 "check"ボタンで照合結果の"G","NG"と顔マークを表示し、"clear"ボタンでリセット動作。
    2020/10/19 閉じるボタンを作る。pixel をmm表示へ変更。.csvデータもmmにすること。
    2020/10/21 公差tolをCSV取得に変更。std表示にtolを表示するように変更。
    '''

import csv
import time
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkFont
import PIL.Image as Image, PIL.ImageTk as ImageTk
#from PIL import Image, ImageTk
import cv2
import numpy as np    #画像の情報が収められたarrayをいじるためにnumpyを用いる。
from matplotlib import pyplot as plt    #画像の表示に用いる。
#from playsound import playsound
from pygame import mixer

camera = 0


print("0")

# tkinterのGUIのクラスを作成
class App(tk.Frame):

    def __init__(self,master=None):        
        tk.Frame.__init__(self, master)
        self.master = master
        self.master.title("The Black Cat")
        mixer.init()        #初期化(ねこの声用)
        
        # opencv キャプチャ設定
        WIDTH,HEIGHT = 640,480 # 2592,1944 1024,768　カメラ画像の縦横幅
        self.cap = cv2.VideoCapture(camera) # opencvカメラキャプチャ
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH) # カメラ画像の横幅設定
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT) # カメラ画像の縦幅設定             
        
        # 画面サイズとワークの実寸合わせ　本当は自動調整にしたいところ
        wmm,hmm = 255, 190 # キャプチャ画面の幅、高さの実寸(mm)
        self.px_x,self.px_y = 4.34, 4.34 #WIDTH/wmm, HEIGHT/hmm = ピクセル数/mm

        #self.flg_m = 0 # マッチング実施済フラグ "check"で'1'に、 "clear"で'0'に
        self.pht =[] # pht: canvas1の画像データ、
        #max_val = jg_thr = jg_x = jg_y = 0
        #jg = 1
        
        #self.jg = 1 #koko
        self.flg_m = 0
        root_w,root_h = 1340, 670 # root(メイン画面）フレームの設定
        root_x,root_y = 0,0 # 表示原点
        self.origin_x, self.origin_y = 200,50 # 撮影画面中の測定原点（ワークの原点pixel)

        root_str = str(root_w)+"x"+str(root_h)+"+"+str(root_x)+"+"+str(root_y) #geometry用文字列
        master.geometry(root_str) # x:y=2:1 縦横サイズと原点位置を文字列で渡す（geometryで設定)
        self.create_widgets() #GUI上のウィジェットを作成するクラスを呼び出す
    

    def create_widgets(self):
        # 結果表示エリア（Frame1)
        #フォント設定
        font_frame = tkFont.Font(family="Lucida Grande",size=15)
        # frame1設定 self.masterはrootを指す
        self.frame1 = tk.LabelFrame(self.master, borderwidth=2,relief='ridge', text="Result",font=font_frame)
        self.frame1.place(relx=0.015, rely=0.03,relwidth=0.53,relheight=0.94) # relはそれぞれのframeの中での相対座標
        # キャンバスエリア（frame1内へ画像表示用のcanvasを作る）
        self.canvas1 = tk.Canvas(self.frame1,borderwidth=2,relief='ridge')#Canvasの作成
        self.canvas1.place(relx=0.015, rely=0.163,relwidth=0.97,relheight=0.82)#Canvasの配置
        #
        font_rsxy = tkFont.Font(family="Lucida Grande", size=20)
        rsxy1 = "1:  X=              Y=             " 
        lb_rsxy1 = tk.Label(self.frame1, text=rsxy1, font=font_rsxy,fg='#000000')
        lb_rsxy1.place(relx=0.45,rely=0)
        rsxy2 = "2:  X=              Y=             " 
        lb_rsxy2 = tk.Label(self.frame1, text=rsxy2, font=font_rsxy,fg='#000000')
        lb_rsxy2.place(relx=0.45,rely=0.073)        

        # 比較テンプレート_1表示エリア（frame2）
        font_s = tkFont.Font(family="Lucida Grande",size = 15)
        # frame2設定
        self.frame2 = tk.LabelFrame(self.master, borderwidth=2,relief='ridge', text="Check Standard 1",font=font_frame)
        self.frame2.place(relx=0.56,rely=0.03,relwidth=0.25,relheight=0.45)
        #正位置(X,Y)と適合率のしきい値をラベルとして表示するためのテンプレ
        self.lb_tx = tk.Label(self.frame2, text ="X= : ",font=font_s)       
        self.lb_tx.place(relx=0.03,rely=0.71)
        self.lb_ty = tk.Label(self.frame2, text ="Y= : ",font=font_s)       
        self.lb_ty.place(relx=0.35,rely=0.71)
        self.lb_tol = tk.Label(self.frame2, text ="tol= : ",font=font_s)       
        self.lb_tol.place(relx=0.7,rely=0.71)
        self.lb_th = tk.Label(self.frame2, text ="threshold= ",font=font_s)       
        self.lb_th.place(relx=0.03,rely=0.85)              
        # キャンバスエリア
        self.canvas2 = tk.Canvas(self.frame2,borderwidth=2,relief='ridge')#Canvasの作成
        # キャンバスバインド
        self.canvas2.place(relx=0.015, rely=0.015,relwidth=0.97,relheight=0.7)#Canvasの配置
        #canvas2.create_image(5,5,image=img_tmp1,anchor="nw")

        # 比較テンプレート_2表示エリア
        self.frame3 = tk.LabelFrame(self.master, borderwidth=2,relief='ridge',text="Check Standard 2",font=font_frame)
        self.frame3.place(relx=0.56,rely=0.52,relwidth=0.25,relheight=0.45)
        #正位置(X,Y)と適合率のしきい値をラベルとして表示する
        self.lb_tx = tk.Label(self.frame3, text ="X= : ",font=font_s)       
        self.lb_tx.place(relx=0.03,rely=0.71)
        self.lb_ty = tk.Label(self.frame3, text ="Y= : ",font=font_s)       
        self.lb_ty.place(relx=0.35,rely=0.71)
        self.lb_tol = tk.Label(self.frame3, text ="tol= : ",font=font_s)       
        self.lb_tol.place(relx=0.7,rely=0.71)
        self.lb_th = tk.Label(self.frame3, text ="threshold= ",font=font_s)       
        self.lb_th.place(relx=0.03,rely=0.85)     
        # キャンバスエリア
        self.canvas3 = tk.Canvas(self.frame3,borderwidth=2,relief='ridge')#Canvasの作成
        # キャンバスバインド
        self.canvas3.place(relx=0.015, rely=0.015,relwidth=0.97,relheight=0.7)#Canvasの配置

        # くろねこ（影）を表示
        self.frame4 = tk.LabelFrame(self.master,borderwidth=0)#, borderwidth=2,relief='ridge'
        self.frame4.place(relx=0.815,rely=0.5,relwidth=0.18,relheight=0.35)
        
        global tkneko # グローバル変数に宣言していないと画像が表示されない（ガベージコレクション）
        img_neko = Image.open("neko_kage.png")
        tkneko = ImageTk.PhotoImage(img_neko)
        print("neko=",tkneko)
        self.neko = tk.Label(self.frame4, image=tkneko, borderwidth=0) #, bg='#d9d9d9'
        self.neko.place(relx=0.1,rely=0.02)           


        #テキストボックス(Part No) 　フレームはrootなので、self.masterになる。
        self.lb_txtb = tk.Label(self.master, text="Part No. :",font=font_s)
        self.lb_txtb.place(relx=0.82,rely=0.0)
        self.txtbox = tk.Entry()
        
        self.txtbox.configure(state="normal",width=15, font=font_s)
        self.txtbox.insert(tk.END,"a0004") # トライ用にとりあえずセット
        self.txtbox.place(relx=0.82, rely=0.05)
        self.txtbox.focus_set() #GUIが起動したらテキストボックスにフォーカスを当てる
        #Loadボタン　txtboxに部品コードを入力後、loadボタンを押すと、テンプレート画像とそれの位置、しきい値情報をCSVから取得し表示する
        self.button1 = tk.Button(self.master, text='Load', command=self.load_clicked,width=9, height=1)
        self.button1.place(relx=0.82, rely=0.11)

        #Checkボタン
        self.button2 = tk.Button(self.master, text='Check', command=self.check_clicked, width=9, height=2)
        self.button2.place(relx=0.82, rely=0.2)
        #Clearボタン
        self.button3 = tk.Button(self.master, text='Clear', command=self.clear_clicked, width=9, height=2)
        self.button3.place(relx=0.9, rely=0.2)
        #Closeボタン
        self.button4 = tk.Button(self.master, text='Close', command=self.master.destroy, width=9, height=2)
        self.button4.place(relx=0.9, rely=0.9)        

        print("1:flg= ",self.flg_m)

        #global delay
        
        self.delay = 15 #[mili sec]　lplp global変数or self.にしないと動画表示されない。update関数でdelayの場所が認識されない。
        print("2:flg= ",self.flg_m)
        _, self.pht = self.cap.read() 
        self.update(self.flg_m,self.pht) # 動画にするため
        

    # Frame1へキャプチャ画像を表示する。app.mainloop()でclass appを繰り返し回して、appからupdateを呼ぶので動画チックになる。
    # マッチング実行したら、実行結果画像（四角付）を静止画で表示。そうでない時はカメラ画像を動画表示
    def update(self,flg,pht):
        #Get a frame from the video source
        #print("3:flg= ",flg)
        global ud
        if flg == 0:
            #ret, vd = self.cap.read()
            _, vd = self.cap.read()
            pht = cv2.cvtColor(vd, cv2.COLOR_BGR2RGB) #カラー変換
            #print("4:flg= ",flg)
            #pht = cv2.resize(pht,(640, 480),cv2.INTER_LINEAR)            

        self.photo = ImageTk.PhotoImage(image = Image.fromarray(pht)) #tkinterで表示できるフォーマットに変換.self必須
        self.canvas1.create_image(15,5, image= self.photo, anchor = tk.NW) #canvas1へ表示
        #print("5:flg= ",flg,delay)
        
        # ↓ マッチング実行したら、実行結果画像（四角付）を静止画で表示。そうでない時はカメラ画像を動画表示
        # flg==1になってそのままafterでself.updateを回すと、flgが0と１を繰り返してしまう。
        # flg==1でafter_cancelすることで表示更新を止めて、結果画像（四角付）を表示して、clearボタンでもとに戻す。
        if flg == 0:
            ud = self.master.after(self.delay, self.update,flg,pht) # delay時間遅延してアップデートする
        else :
            self.master.after_cancel(ud) #https://daeudaeu.com/tkinter_after/    
      
    # テンプレートの正解位置を各フレームに表示する
    # frame2,3内で相対位置を使っているため、関数化できた。
    def lbl_std(self,frm,x,y,tol,thr):
        font_s = tkFont.Font(family="Lucida Grande",size = 15)        
        self.lb_stdx = tk.Label(self.frm, text =x ,font=font_s)       
        self.lb_stdx.place(relx=0.16,rely=0.71)
        self.lb_stdy = tk.Label(self.frm, text =y ,font=font_s)       
        self.lb_stdy.place(relx=0.48,rely=0.71)
        self.lb_stdtol = tk.Label(self.frm, text =tol ,font=font_s)       
        self.lb_stdtol.place(relx=0.87,rely=0.71)        
        self.lb_stdth = tk.Label(self.frm, text =thr,font=font_s)       
        self.lb_stdth.place(relx=0.4,rely=0.85)
    
    
    # frame1へマッチング結果のx,y,適合率(thr) を表示
    # check_clicked()から呼び出す
    def lbl_rslt(self,no,x,y,thr,jg_thr,jg_x,jg_y):
        x = round(x / self.px_x)
        y = round(y / self.px_y)
        color_x = color_y = color_thr = '#000000' #文字色 黒
        if no == 1:     # テンプレート 1との比較前にjg（ジャッジ）を１にしておく。
            self.jg = 1 # ここでしておかないと"clear"ボタンからの呼び出しの時に前回がNGだと0が残ってしまう
            
        if not(jg_x and jg_y and jg_thr):
            self.jg = 0 # インスタンス変数（self.)になっていないとなぜかエラーが出る。
            
            print("kokode!")

        if self.jg == 1:   
            img_face = Image.open("niko.png")
            txt = "OK !"
            clr = '#1116ff' # Blue
            
        else:
            img_face = Image.open("oko.png")
            txt = "NG !"
            clr = '#ff1606' # Red
            
        global tkimg # global変数にしないと画像が表示されない。ガベージコレクションによると思われる。
        # https://daeudaeu.com/create_image_problem/#i-6
        if no == 2:
            print(img_face)
            tkimg = ImageTk.PhotoImage(img_face)
            self.face = tk.Label(self.frame1, image=tkimg, bg='#d9d9d9')
            self.face.place(relx=0.04,rely=0.02)           
            font_rs = tkFont.Font(family="Lucida Grande", size=40)
            self.lb_rslt = tk.Label(self.frame1, text=txt,font=font_rs,fg=clr)#←青　赤は#ff1606
            self.lb_rslt.place(relx=0.2,rely=0.00)
            if self.jg == 1:
                mixer.music.load("./sound/cat15.mp3") # OK ニャーオン
            else:
                mixer.music.load('./sound/cat-threat1.mp3') # NG シャー
            mixer.music.play(0)
        
        if jg_x == 0: # ジャッジ（判定）がNGだったら文字を赤にする
            color_x = '#ff0000'
        if jg_y == 0:
            color_y = '#ff0000'
        if jg_thr == 0:
            color_thr = '#ff0000'    
   
        thr = round(thr,3)

        # ↓元はテンプ１と２の結果をlb_rslt1,2,3を２回回していたが、
        # clearボタンで削除するためにlb_rslt４，５，６を使うことに↓。
        # ラベルへ計測結果を表示
        print("lb_rslt x=",x)
        font_rsxy = tkFont.Font(family="Lucida Grande", size=20)
        if no == 1 : # no==1はテンプ１との比較結果を受け取ったとき
            self.lb_rslt1 = tk.Label(self.frame1, text=x, font=font_rsxy,fg=color_x)
            self.lb_rslt1.place(relx=0.56,rely=0) # lb_rslt1はテンプ１のX位置の測定結果
            self.lb_rslt2 = tk.Label(self.frame1, text=y, font=font_rsxy,fg=color_y)
            self.lb_rslt2.place(relx=0.72,rely=0) # lb_rslt2はテンプ１のy位置の測定結果
            self.lb_rslt3 = tk.Label(self.frame1, text=thr, font=font_rsxy,fg=color_thr)
            self.lb_rslt3.place(relx=0.85,rely=0) # lb_rslt3はテンプ１の適合率の測定結果
        else: # テンプ2との比較結果を受け取ったとき
            self.lb_rslt4 = tk.Label(self.frame1, text=x, font=font_rsxy,fg=color_x)
            self.lb_rslt4.place(relx=0.56,rely=0.073) # lb_rslt4はテンプ2のX位置の測定結果
            self.lb_rslt5 = tk.Label(self.frame1, text=y, font=font_rsxy,fg=color_y)
            self.lb_rslt5.place(relx=0.72,rely=0.073) # lb_rslt5はテンプ2のX位置の測定結果
            self.lb_rslt6 = tk.Label(self.frame1, text=thr, font=font_rsxy,fg=color_thr)
            self.lb_rslt6.place(relx=0.85,rely=0.073)# lb_rslt6はテンプ2の適合率の測定結果
         
        
    # loadボタンを押した時の動作
    # txtboxへ入力された部品コードと同名のフォルダから同名のCSVを開いてテンプレートの正解位置としきい値を取得
    # 部品コードと同名の画像を取得（frame2,3用の２つ）。frame(canvas)サイズに合わせてresizeしてcanvasに表示する。
    def load_clicked(self):
        std = []
        print('load_clicked')
        global rs_img1, rs_img2 # グローバル変数にしないと画像が表示されない　https://daeudaeu.com/create_image_problem/
        global temp1,temp2 # テンプレート画像をcheck_clickedで使うため
        global std1_x, std1_y, std1_thr # temp1の表示位置、合格しきい値
        global std2_x, std2_y, std2_thr # temp2の表示位置、合格しきい値
        global tol1, tol2 # x,y公差
        stdno = self.txtbox.get() # ID(PartNo)を取得

        #CSVをリストへ取り込み。結構ハマった。
        with open('./standard' + '/' + stdno + '/' + stdno + '.csv') as f:
            for st in csv.reader(f):
                std.append(st)

        for i in range(1,3): # テンプレート情報1,2を取得
            print(i)
            
            r = i - 1
            x,y,tol,thr = int(std[r][0]),int(std[r][1]),int(std[r][2]),float(std[r][3]) # CSVから取得したデータ
            name = './standard' + '/' + stdno + '/' + stdno + '_' + str(i) + '.png'
            img = Image.open(name) # テンプレート画像を取得
            temp = cv2.imread(name,0) #テンプレートマッチング用に読込（,0でグレースケール読込）　上の行のimgは型式が違うためcvでは使えない

            if i == 1 : # frame2へ画像を表示
                std1_x = x # canvas2のラベル表示用。値はマスタCSVから取得
                std1_y = y
                tol1 = tol
                std1_thr = thr
                temp1 = temp # テンプレートマッチング用
                rs_img1 = self.resize(img) # テンプレート画像をリサイズ
                self.canvas2.create_image(5,5,image=rs_img1,anchor="nw") # canvas2へ画像を表示
                self.frm = self.frame2
                
            if i == 2 : # frame3へ画像を表示
                std2_x = x
                std2_y = y
                tol2 = tol
                std2_thr = thr                
                temp2 = temp # テンプレートマッチング用
                rs_img2 = self.resize(img)
                self.canvas3.create_image(5,5,image=rs_img2,anchor="nw")
                print(i)
                self.frm = self.frame3
                
            self.lbl_std(self.frm, x,y,tol,thr) # Frame2,3のラベルへ表示
            

    # checkボタンを押した時の動作
    # カメラ画像を読込み、上のload_clicked()で読み込んだテンプレート画像1,2をマッチングを実行
    # 計測結果の値(x,y,適合率）をlbl_rslt()を呼んで表示
    # マッチング結果の四角を描画。OKは青、ngは赤
    def check_clicked(self):
        #self.clear_clicked()
        if self.flg_m == 0:
            print("check_clicked")
            self.flg_m = 1 # マッチング実施済みフラグ
            ret, vd = self.cap.read() #キャプチャ画像読込
            print("in the middle self.flg_m = ",self.flg_m)
            img = cv2.cvtColor(vd,cv2.COLOR_RGB2GRAY)  #読み込んだ画像のグレイスケール化
            self.pht = cv2.cvtColor(vd,cv2.COLOR_BGR2RGB)   #canvasへの表示用。これがないと色がおかしい              
            
            # テンプレート画像1,2とマッチング実施
            for i in range(1,3): # 1〜3ではなく１〜２
                jg_thr,jg_x,jg_y = 0, 0, 0 # 適合率、x,yの判定結果　1:OK,0:NG 四角の色を赤、青に変える用
                
                #マッチングテンプレートを実行
                #比較方法はcv2.TM_CCOEFF_NORMEDを選択
                if i == 1 : # テンプレート１と照合
                    print(img.shape,temp1.shape)
                    temp = temp1 # テンプレート画像１
                    std_x, std_y, std_thr = round(std1_x * self.px_x), round(std1_y * self.px_y), std1_thr # テンプ１の正解位置、しきい値             
                    tol_p = tol1 * self.px_x
                else: # テンプレート2と照合
                    temp = temp2
                    std_x, std_y, std_thr = round(std2_x * self.px_x), round(std2_y * self.px_y), std2_thr
                    tol_p = tol2 * self.px_x
                #std_x = std_x * self.px_x # mmからピクセルに変換
                #std_y = std_y * self.px_y
                    
                result = cv2.matchTemplate(img, temp, cv2.TM_CCOEFF_NORMED) #マッチング実行
                print("finished self.self.flg_m = ",self.flg_m)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result) #実行結果からx,y,適合率を取得
                top_left = max_loc # 適合率maxの位置(max_loc)を四角を表示する位置へ（top_left）
                w, h = temp.shape[::-1] # テンプ画像のサイズ取得
                bottom_right = (top_left[0] + w, top_left[1] + h) # 四角の右下座標
                
                x, y = top_left[0]-self.origin_x, top_left[1]-self.origin_y                

                print ("self.px_x= ",self.px_x, " self.px_y= ",self.px_y)
                print ("No.",i , " max_val:", max_val, "  thr: ", std_thr)           
                print ("No.",i , "max_loc:", max_loc)
                print ("No.",i , "top_left_x",x, "  std_x: ", std_x) 
                print ("No.",i , "top_left_y",y, "  std_y: ", std_y)
                print ("No.",i ,  "  tol_p: ", tol_p)

                # 判定　合格なら四角を青、不合格なら赤に。jg_ =1がokフラグ
                if max_val >= std_thr: # 適合率としきい値を比較
                    jg_thr = 1
                if (std_x - tol_p) <= x <= (std_x + tol_p): # X座標±公差と測定値を比較
                    jg_x = 1
                if (std_y - tol_p) <= y <= (std_y + tol_p): # y座標±公差と測定値を比較
                    jg_y = 1
                if jg_thr == 1 and jg_x == 1 and jg_y == 1: # 全て合格なら青
                    color =(0,0,255)
                else:
                    color =(255,0,0) # 一つでもNGなら赤
                print('jg_x:' , jg_x, std_x - tol_p,"<=", x,"<=", std_x + tol_p)
                print('jg_y:' , jg_y, std_y - tol_p,"<=", y,"<=", std_y + tol_p)

                cv2.rectangle(self.pht,top_left, bottom_right, color, 2)

                print("rect self.flg_m= ",self.flg_m)
                
                self.lbl_rslt(i,x,y,max_val,jg_thr,jg_x,jg_y) # 計測結果の表示(frame1)
            print("update mae")
            self.update(self.flg_m,self.pht)

    # 結果表示をクリアする。結果画像（四角付）を消してキャプチャ映像に。x,y,thrの表示も消す。   
    def clear_clicked(self):
        self.flg_m = 0 # マッチング実行済フラグ
        # x,y,thrの表示を消す。値の表示は lbl_rslt()で行っている。
        self.lb_rslt1.place_forget() # 表示さたラベルを消すメソッド
        self.lb_rslt2.place_forget() # self.がついてないと消えない。
        self.lb_rslt3.place_forget()
        self.lb_rslt4.place_forget()
        self.lb_rslt5.place_forget()
        self.lb_rslt6.place_forget()
        self.lb_rslt.place_forget()
        self.face.place_forget()
        
        #jg = 1
        #print("self.flg_m= ",self.flg_m,"  pht= ",pht)
        self.update(self.flg_m,self.pht)        
        
    # テンプレート画像をframeサイズに合わせるようにリサイズする。
    def resize(self,img):
        img_w,img_h = img.size # テンプレート画像のサイズを取得
        r_xy1 = img_w / img_h # 画像の縦横比率を計算
         # 縦横比によってcanvasの大きさに合わせる
        if r_xy1 > 1.54 :
            resize_img_w = 277
            resize_img_h = int(277 / r_xy1)
        else:
            resize_img_h = 180
            resize_img_w = int(180 * r_xy1)
        resize_img = img.resize((resize_img_w, resize_img_h),Image.BICUBIC)
        resize_img = ImageTk.PhotoImage(resize_img)
        return resize_img
       
        
# メインループ
def main():

    root = tk.Tk()
    root.attributes("-zoomed","1")
    app = App(master=root)
    app.mainloop()
    
if __name__ == "__main__":
    main()  

