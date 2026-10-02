from statistics import mean, median, stdev
def aggregate_metrics(values): return {"count":len(values),"mean":mean(values) if values else 0,"median":median(values) if values else 0,"min":min(values) if values else 0,"max":max(values) if values else 0,"std":stdev(values) if len(values)>1 else 0}
