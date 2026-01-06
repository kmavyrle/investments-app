def update_tick_data(old_file_dir = r"C:\Users\kmavy\Documents\mydocs\My Docs\4Sight\attachments\tick_data.csv"):
    """
    Function updates the latest tick data for listed assets
    Reads the existing data and checks for missing data
    If no change it only pulls latest data for the day.
    """
    prev_data = pd.read_csv(old_file_dir,index_col = 0)
    target_date_range = pd.bdate_range(start='2023-01-01', end=datetime.datetime.today().strftime("%Y-%m-%d"), freq='D')
    curr_date_range = set(prev_data.index)
    missing_dates = [dt for dt in target_date_range if dt not in curr_date_range]
    if not missing_dates:
        print("Data is the latest; updating only latest print")
        df = [mt.get_tick_data(asset,'1d',2) for asset in asset_map.values()]
        df = pd.concat(df)
        df = pd.concat([df, prev_data])
        df = df.groupby('asset').apply(lambda x: x.drop_duplicates())
        df.index = df.index.get_level_values(1)
        df.to_csv('tick_data.csv')       
    else:
        print("Dates missing; updating data from server")
        earliest = min(missing_dates)
        count = datetime.datetime.today() - earliest
        daycount = count.days
        #print()
        df = [mt.get_tick_data(asset,'1d',daycount) for asset in asset_map.values()]
        df = pd.concat(df)
        #df.to_csv('tick_data.csv')
        df = pd.concat([df, prev_data])
        df = df.groupby('asset').apply(lambda x: x.drop_duplicates())
        df.index = df.index.get_level_values(1)
        df.to_csv('tick_data.csv')



