#include <iostream>
#include <vector>

using namespace std;

int main()
{
    long long n;
    long long m;
    cin>>n>>m;
    const int MAXN = 2e5+5;
    long long heights[MAXN];
    int h;

    for(int i = 0; i < n; i++) cin>>heights[i];
    for(int i = 0; i < m; i++)
    {
        int x;
        cin>>x;
        h = 0;
        for(int j = 0; j < n && h < x; j++)
        {
            if(h < heights[j])
            {
                int diff = (x > heights[j])? heights[j] - h: x - h;
                heights[j] += diff;
                h += diff;
            }
        }
    }
    for(int i = 0; i < n; i++)
    {
        cout<<heights[i]<<endl;
    }
}
