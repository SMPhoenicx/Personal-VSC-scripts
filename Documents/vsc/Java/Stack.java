package Java;

import javax.swing.text.Document;
public class Stack
{
    private Document[] arr;
    private int counter = 0; //keeps track of the current location of a number, the "index"
    public Stack(int size)
    {
        arr = new Document[size];
    }
    public boolean isEmpty() //checks if it is empty by checking if the index is 0
    {
        if(counter == 0)
        {
            return true;
        }
        return false;
    }
    public boolean isFull() //checks if it is full by checking if the index is at the end
    {
        if(counter == arr.length)
        {
            return true;
        }
        return false;
    }
    public void push(Document x) //checks if array is full and then places the number in the array
    {
        if(!this.isFull())
        {
            arr[counter] = x;
            counter++;
        }
        else
        {
            System.out.println("Stack is full");
        }
    }
    public Document pop() //checks if array is empty or not and then returns the element
    {
        if(!this.isEmpty())
        {
            counter--;
            return arr[counter];
        }
        else
        {
            System.out.println("Stack is empty");
        }
        return null;
    }

    public void clear()
    {
        arr = new Document[arr.length];
        counter = 0;
    }

    public Document peek() 
    {
        return arr[counter];
    }
}
