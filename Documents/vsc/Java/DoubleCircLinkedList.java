package Java;

public class DoubleCircLinkedList<T> 
{
    public DLink<T> head; //head of list
    public DLink<T> tail; //tail of list

    public DoubleCircLinkedList()
    {
        head = null; 
        tail = null;
    }

    public boolean isEmpty()
    {
        return head == null || tail == null;
    }

    public void insertAtBeginning(T input)
    {
        DLink<T> temp = new DLink<T>(input);
        if(head != null) //inserts
        {
            head.prev.addNext(temp);
            temp.addPrev(head.prev);
            head.addPrev(temp);
            temp.addNext(head);
            head = temp;
        }
        else //if first time inserting, then set tail same as head
        {
            head = temp;
            head.addNext(head);
            head.addPrev(head);
            tail = head;
        }
    }

    public void insertAtEnd(T input)
    {
        DLink<T> temp = new DLink<T>(input); 
        if(tail != null) //inserts
        {
            tail.next.addPrev(temp);
            temp.addNext(tail.next);
            tail.addNext(temp);
            temp.addPrev(tail);
            tail = temp;
        }
        else //if first time inserting, then set head same as tail
        {
            tail = temp;
            tail.addNext(tail);
            tail.addPrev(tail);
            head = tail;
        }
    }

    public boolean insertAfter(T key, T input)
    {
        if(isEmpty())
        {
            return false;
        }
        DLink<T> temp = head; //temporary storage

        do
        {
            if(head.value.equals(key))
            {
                DLink<T> tempTwo = new DLink<T>(input); //new link
                tempTwo.addNext(head.next); //insert in and link it with others
                head.next.addPrev(tempTwo);
                head.addNext(tempTwo);
                tempTwo.addPrev(head);
                head = temp;
                return true;
            }
            else
            {
                head = head.next; //iterate
            }
        }
        while(head != temp);

        head = temp; //reinstate
        return false;
    }

    public DLink<T> deleteFirst()
    {
        if(!isEmpty())
        {
            DLink<T> temp = head; //store link
            if(head.next == head.prev)
            {
                head = null;
                return temp;
            }
            head.prev.addNext(head.next);
            head.next.addPrev(head.prev);
            head = head.next; //set head to next link
            return temp;
        }
        else
        {
            System.out.println("List Empty");
        }
        return null;
    }

    public DLink<T> deleteLast()
    {
        if(!isEmpty())
        {
            DLink<T> temp = tail; //store link
            if(tail.prev == temp)
            {
                DLink<T> tempTwo = tail;
                tail = null;
                return tempTwo;
            }
            tail = tail.prev;
            tail.addNext(temp.next);
            temp.next.addPrev(tail);
            return temp;
        }
        else
        {
            System.out.println("List Empty");
        }
        return null;
    }

    public DLink<T> deleteLink(T key)
    {
        if(isEmpty())
        {
            return null;
        }
        DLink<T> temp = head; //temp storage
        if(head.next == head.prev)
        {
            head = null;
            return temp;
        }
        if(tail.value.equals(key)) //if tail, return tail
        {
            tail.prev.addNext(tail.next);
            tail.next.addPrev(tail.prev);
            tail = tail.prev;
            return tail;
        }
        if(head.value.equals(key)) //if head, return head
        {
            head.prev.addNext(head.next);
            head.next.addPrev(head.prev);
            head = head.next;
            return temp;
        }
        while(head.next.next != temp) //rest of the cases
        {
            if(head.next.value.equals(key))
            {
                DLink<T> holder = head.next;
                head.addNext(holder.next);
                holder.next.addPrev(head);
                head = temp;
                return holder;
            }
            else
            {
                head = head.next;
            }
        }
        if(head.next.value.equals(key))
        {
            DLink<T> holder = head.next;
            head.addNext(holder.next);
            holder.next.addPrev(head);
            head = temp;
            System.out.println("final"+tail.value);
            return holder;
        } 

        return null;
    }

    public void display()
    {
        if(!isEmpty())
        {
            DLink<T> temp = head; 
            while(head.next != temp) //iterate through links
            {
                System.out.print(head.value+" "); //print linkn values
                head = head.next;
            }
            System.out.print(head.value + "\n"); //print final link value
            head = temp;
        }
        else
        {
            System.out.println("List Empty");
        }
    }

}
