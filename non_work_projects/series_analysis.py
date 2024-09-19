import numpy as np

window_size = 5
k = window_size

series_list = [[7, 87, 15, 75, 41],\
[81, 80, 74, 49, 61],\
[38, 74, 37, 69, 50, 93, 49],\
[76, 30, 14, 41, 62, 3, 48, 5, 27, 89, 42, 49, 59, 59, 96],\
[99, 27, 70, 43, 48, 12, 77, 33, 4],\
[28, 45, 73, 85, 83, 10, 55, 99, 13, 87],\
[40, 0, 47, 93, 40, 54, 71],\
[55, 2, 59, 65, 58, 19, 55],\
[28, 41, 41, 18, 100, 19, 4],\
[21, 37, 60, 99, 54, 79, 47, 29]]



s = series_list[3]
n = len(s)
assert k <= n
windows = [np.array(s[i:i+k]) for i in range(n-k+1)]
means_stds = zip([np.mean(w) for w in windows], [np.std(w) for w in windows])
tolerance = 2
tolerance_bands = [(mean-(2*std), mean+(2*std)) for (mean,std) in means_stds]
outliers = [w[(w < tb[0]) | (w > tb[1])] for (w,tb) in zip(windows, tolerance_bands)]
print(list(zip(windows,outliers)))

