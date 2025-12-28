import pandas as pd
from remove_noise import filter_data_by_column  # プログラム本体(main.py)から関数を呼ぶ


def test_csv_filtering(tmp_path):
    # 1. 一時的なテスト用CSVファイルを作成
    input_file = tmp_path / "input.csv"
    output_file = tmp_path / "output.csv"

    # テストデータ: 1行目は残るはず、2行目は「ノイズ」なので消えるはず
    df = pd.DataFrame(
        {
            "sentiment_or_noise": ["ポジティブ", "ノイズ"],
            "is_location_related": [True, True],
            "user_attribute": ["住民", "住民"],
        }
    )
    df.to_csv(input_file, index=False)

    # 2. 関数を実行
    filter_data_by_column(
        input_path=str(input_file),
        output_path=str(output_file),
        process_type="csv",
        target_col="sentiment_or_noise",
        exclude_values=["ノイズ"],  # 除外対象
        location_col="is_location_related",
        user_attr_col="user_attribute",
        exclude_user_attrs=["それ以外"],
    )

    # 3. 結果の検証
    df_result = pd.read_csv(output_file)
    assert len(df_result) == 1  # 1行だけ残っているか
    assert df_result.iloc[0]["sentiment_or_noise"] == "ポジティブ"  # 正しいデータか
