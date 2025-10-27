/*
ID: sumanm
LANG: C++
TASK: gift1
*/
#include <iostream>
#include <fstream>
#include <string.h>
using namespace std;

int num;
string people[10];
int balance[10];
    
int lookup(string name)
{
    for(int i = 0; i < num; i++) {
        if(name==people[i]) {
            return i;
        }
    }
    return 0;
}
int main(){
	ofstream fout ("gift1.out");
    ifstream fin ("gift1.in");
    int np;
    fin>>np;
    for(int i = 0; i < np; ++i)
    {
        fin>>people[i];
        num++;
    }
    for(int i = 0; i < num; ++i)
    {
        string name;
        int money, numP;
        fin>>name>>money>>numP;
        int index = lookup(name);
        for(int j = 0; j < numP; j++)
        {
            string receiver;
            fin>>receiver;
            int rIndex = lookup(receiver);
            balance[index] -= money/numP;
            balance[rIndex] += money/numP;
        }
    }
    for(int i = 0; i < np; i++)
    {
        fout<<people[i]<<" "<<balance[i]<<endl;
    }
    exit(0);
}
