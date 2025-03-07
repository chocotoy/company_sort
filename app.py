import streamlit as st
import pandas as pd
import numpy as np
import os
import tempfile
import hashlib

# パスワードによる保護
def check_password():
    def password_entered():
        # デバッグ用：入力されたパスワードと設定されたパスワードを確認
        input_password = st.session_state["password"]
        correct_password = "369369"  # 直接パスワードを設定
        
        if input_password == correct_password:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
            st.error(f"パスワードが正しくありません")

    if "password_correct" not in st.session_state:
        st.text_input(
            "パスワードを入力してください", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        return False
    
    return st.session_state["password_correct"]

# メイン処理
def main():
    # アプリケーションのタイトルを設定
    st.title('企業データ分析ツール')
    st.write('CSVファイルをアップロードして、企業データを分析できます。')

    # キャッシュをクリア
    if 'first_run' not in st.session_state:
        st.session_state.first_run = True
        st.cache_data.clear()

    # ファイルアップロード機能
    uploaded_file = st.file_uploader("企業データCSVファイルをアップロード", type="csv")

    if uploaded_file is not None:
        # 一時ファイルとして保存
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        try:
            # CSVファイルを読み込む
            # エンコーディングを指定してCSVファイルを読み込む
            try:
                # まずUTF-8で試す（BOMありの場合も考慮）
                df = pd.read_csv(tmp_path, encoding='utf-8-sig')
                # 文字列カラムの処理を追加
                for col in df.select_dtypes(include=['object']).columns:
                    df[col] = df[col].astype(str).str.strip()
            except UnicodeDecodeError:
                try:
                    # 次にShift-JIS (cp932)で試す
                    df = pd.read_csv(tmp_path, encoding='cp932')
                    # 文字列カラムの処理を追加
                    for col in df.select_dtypes(include=['object']).columns:
                        df[col] = df[col].astype(str).str.strip()
                except UnicodeDecodeError:
                    # それでも失敗する場合はLatin-1で試す（ほとんどのエンコーディングを読める）
                    df = pd.read_csv(tmp_path, encoding='latin-1')
                    # 文字列カラムの処理を追加
                    for col in df.select_dtypes(include=['object']).columns:
                        df[col] = df[col].astype(str).str.strip()
            
            # データの基本情報を表示
            st.subheader('データの基本情報')
            st.write(f'行数: {df.shape[0]}, 列数: {df.shape[1]}')
            
            # カラム情報を表示
            st.subheader('カラム情報')
            st.write(df.columns.tolist())
            
            # データのプレビューを表示
            st.subheader('データプレビュー')
            st.dataframe(df.head())
            
            # サイドバーにフィルタリングオプションを追加
            st.sidebar.header('データフィルタリング')
            
            # 数値カラムと文字列カラムを分ける
            numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
            categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
            
            # フィルタリング用のカラムを選択
            filter_cols = st.sidebar.multiselect(
                'フィルタリングするカラムを選択',
                options=df.columns.tolist(),
                default=[]
            )
            
            # フィルタリング条件を設定
            filtered_df = df.copy()
            
            for col in filter_cols:
                if col in numeric_cols:
                    # 数値カラムの場合、範囲でフィルタリング
                    min_val = float(filtered_df[col].min())
                    max_val = float(filtered_df[col].max())
                    
                    filter_range = st.sidebar.slider(
                        f'{col}の範囲',
                        min_value=min_val,
                        max_value=max_val,
                        value=(min_val, max_val)
                    )
                    
                    filtered_df = filtered_df[(filtered_df[col] >= filter_range[0]) & 
                                              (filtered_df[col] <= filter_range[1])]
                
                elif col in categorical_cols:
                    # カテゴリカラムの場合、選択肢でフィルタリング
                    # 元のデータフレームから一意の値を取得するように修正
                    unique_values = df[col].dropna().unique().tolist()
                    
                    # 業種カラムの場合、特別な処理を追加
                    if col == '業種':
                        # 業種カラムの値を文字列として明示的に処理
                        unique_values = [str(val).strip() for val in unique_values]
                        # 重複を削除
                        unique_values = list(dict.fromkeys(unique_values))
                        # キャッシュをクリア
                        st.cache_data.clear()
                        
                        # 業種の選択肢を直接指定する方法も試す
                        if '電車' in unique_values:
                            st.sidebar.warning("「電車」という業種が含まれています。これは表示の問題かもしれません。")
                        
                        # デバッグ情報を表示
                        with st.expander("業種データのデバッグ情報"):
                            st.write("業種の一意な値:", unique_values)
                            st.write("業種カラムのサンプル:", df['業種'].head(10).tolist())
                        
                        # 代替表示方法を追加
                        st.sidebar.write("---")
                        st.sidebar.write("代替業種選択方法:")
                        alt_selected = {}
                        for val in unique_values:
                            alt_selected[val] = st.sidebar.checkbox(f"業種: {val}", value=False, key=f"alt_check_{val}_{hashlib.md5(val.encode()).hexdigest()[:8]}")
                        
                        # 代替選択方法の結果を反映
                        alt_selected_values = [val for val, selected in alt_selected.items() if selected]
                        if alt_selected_values:
                            # 代替選択方法の結果をmultiselect選択に反映
                            selected_values = alt_selected_values
                        else:
                            # デフォルトですべて選択
                            selected_values = unique_values
                    
                    # ユニークなキーを生成
                    key_str = f"select_{col}_{hashlib.md5(str(unique_values).encode()).hexdigest()[:8]}"
                    
                    # 業種以外のカラムの場合は通常のmultiselect
                    if col != '業種':
                        selected_values = st.sidebar.multiselect(
                            f'{col}を選択',
                            options=unique_values,
                            default=[],  # デフォルトを空のリストに変更
                            key=key_str  # ユニークなキーを使用
                        )
                    
                    # 選択された値が実際にデータセットに存在するかを確認
                    valid_selected_values = [value for value in selected_values if value in unique_values]
                    
                    if valid_selected_values:
                        filtered_df = filtered_df[filtered_df[col].isin(valid_selected_values)]
                    elif selected_values and not valid_selected_values:
                        st.sidebar.warning(f"選択された値 {', '.join(selected_values)} はデータセットに存在しません。")
            
            # フィルタリング結果を表示
            st.subheader('フィルタリング結果')
            
            # フィルタリング統計情報を表示
            total_rows = df.shape[0]
            filtered_rows = filtered_df.shape[0]
            filtered_percentage = (filtered_rows / total_rows * 100) if total_rows > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("元データ件数", f"{total_rows:,}")
            with col2:
                st.metric("フィルタリング後件数", f"{filtered_rows:,}")
            with col3:
                st.metric("データ残存率", f"{filtered_percentage:.1f}%")
            
            # フィルタリング条件ごとの内訳を表示
            if filter_cols and st.checkbox('フィルタリング条件ごとの内訳を表示'):
                st.subheader('フィルタリング条件ごとの内訳')
                for col in filter_cols:
                    if col in numeric_cols:
                        # 数値カラムの場合、範囲でのフィルタリング結果を表示
                        st.write(f"**{col}** の範囲: {filter_range[0]} から {filter_range[1]}")
                        in_range_count = df[(df[col] >= filter_range[0]) & (df[col] <= filter_range[1])].shape[0]
                        in_range_percentage = (in_range_count / total_rows * 100) if total_rows > 0 else 0
                        st.write(f"条件に合致: {in_range_count:,}件 ({in_range_percentage:.1f}%)")
                    
                    elif col in categorical_cols:
                        # カテゴリカラムの場合、選択された値ごとの件数を表示
                        st.write(f"**{col}** の選択値:")
                        # 選択された値が実際にデータセットに存在するかを確認
                        # 修正: filtered_dfではなく、元のdfに対して検証するのではなく、同じunique_valuesを使用する
                        if not valid_selected_values and selected_values:
                            st.write(f"選択された値 {', '.join(selected_values)} はデータセットに存在しません。")
                        
                        for value in valid_selected_values:
                            value_count = df[df[col] == value].shape[0]
                            value_percentage = (value_count / total_rows * 100) if total_rows > 0 else 0
                            st.write(f"- {value}: {value_count:,}件 ({value_percentage:.1f}%)")
            
            st.dataframe(filtered_df)
            
            # データの統計情報を表示
            st.subheader('統計情報')
            if st.checkbox('数値データの統計情報を表示'):
                st.write(filtered_df.describe())
            
            # データのダウンロード機能
            if st.button('フィルタリング結果をCSVでダウンロード'):
                # 文字化け防止のためにBOMつきUTF-8でエンコード
                # バイナリデータとして直接エンコードすることで文字化けを防止
                csv_data = filtered_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="CSVファイルをダウンロード",
                    data=csv_data,
                    file_name="filtered_data.csv",
                    mime="text/csv"
                )
        
        except Exception as e:
            st.error(f'エラーが発生しました: {e}')
        
        finally:
            # 一時ファイルを削除
            os.unlink(tmp_path)
    else:
        st.info('CSVファイルをアップロードしてください。')

    # アプリケーションの使い方
    with st.expander("アプリケーションの使い方"):
        st.write("""
        1. 「企業データCSVファイルをアップロード」ボタンをクリックしてCSVファイルを選択します。
        2. サイドバーでフィルタリングしたいカラムを選択します。
        3. 選択したカラムに応じて、フィルタリング条件を設定します。
        4. フィルタリング結果が自動的に表示されます。
        5. 「フィルタリング結果をCSVでダウンロード」ボタンをクリックすると、結果をCSVファイルとしてダウンロードできます。
        """)

    # フッター
    st.markdown("---")
    st.markdown("© 2025 OSL-LIghting 企業データ分析ツール")

if __name__ == "__main__":
    if check_password():
        main()