#include <iostream>
#include <string>
#include <algorithm>
#include <vector>
using namespace std;

int main()
{
    int n, m;
    string order;
    vector<int> capacities;
    vector<int> has;
    cin>>n>>m>>order;

    int x;
    for(int i = 0; i < n; i++)
    {
        cin>>x;
        capacities.push_back(x);
        has.push_back(x);
    }

    for(int i = 0; i < m; i++)
    {
        
    }
    int total = 0;

    for(int x: has)
    {
        total += x;
    }

    cout<<total<<endl;
}